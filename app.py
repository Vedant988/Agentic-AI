"""
app.py — Streamlit UI for the Competitive Intelligence Multi-Agent System
Clean, human-readable interface showing:
  - Step decomposition before execution
  - Live planning trace from Orchestrator
  - Agent progress as a visual timeline
  - Final report in a clean readable card
"""

import sys, time, threading, json
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CompIntel — Competitive Intelligence",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background: #111318; }
.block-container { padding: 2rem 2.5rem 4rem; max-width: 1200px; }

/* ── Typography ── */
h1, h2, h3 { color: #f0f2f5; letter-spacing: -0.3px; }
p, li { color: #9aa3af; line-height: 1.6; }

/* ── Header ── */
.app-header { margin-bottom: 2rem; }
.app-title {
    font-size: 2rem; font-weight: 700;
    background: linear-gradient(135deg, #e2e8f0 0%, #94a3b8 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0 0 0.25rem;
}
.app-subtitle { color: #64748b; font-size: 0.875rem; margin: 0; }
.tech-pills { display: flex; gap: 0.5rem; margin-top: 0.75rem; flex-wrap: wrap; }
.pill {
    background: #1e2430; border: 1px solid #2d3748; color: #94a3b8;
    padding: 3px 10px; border-radius: 20px; font-size: 0.72rem;
    font-family: 'JetBrains Mono', monospace; letter-spacing: 0.02em;
}

/* ── Section ── */
.section-label {
    font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: #4a6fa5; margin: 2rem 0 0.75rem;
    display: flex; align-items: center; gap: 0.5rem;
}
.section-label::after {
    content: ''; flex: 1; height: 1px; background: #1e2430;
}

/* ── Input ── */
.stTextInput input {
    background: #1a1f2e !important; border: 1px solid #2d3748 !important;
    color: #e2e8f0 !important; border-radius: 8px !important;
    font-size: 0.95rem !important; padding: 0.6rem 1rem !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.stTextInput input:focus {
    border-color: #4a6fa5 !important;
    box-shadow: 0 0 0 3px rgba(74,111,165,0.15) !important;
}
.stTextInput input::placeholder { color: #4a5568 !important; }

/* ── Run Button ── */
div[data-testid="stButton"] > button {
    background: #4a6fa5 !important; color: #fff !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; font-size: 0.88rem !important;
    padding: 0.62rem 1.5rem !important; height: 100% !important;
    transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
}
div[data-testid="stButton"] > button:hover {
    background: #3d5f8a !important;
    box-shadow: 0 4px 16px rgba(74,111,165,0.35) !important;
    transform: translateY(-1px) !important;
}

/* ── Execution plan table ── */
.plan-table { width: 100%; border-collapse: collapse; }
.plan-table th {
    background: #161b27; color: #4a6fa5; font-size: 0.7rem;
    text-transform: uppercase; letter-spacing: 0.1em;
    padding: 8px 14px; border-bottom: 1px solid #1e2430;
    font-weight: 600; text-align: left;
}
.plan-table td {
    padding: 10px 14px; border-bottom: 1px solid #161b27;
    font-size: 0.83rem; vertical-align: middle; color: #9aa3af;
}
.plan-table tr:last-child td { border-bottom: none; }
.plan-table tr:hover td { background: #161b27; }
.step-num {
    font-family: 'JetBrains Mono', monospace; color: #4a6fa5;
    font-weight: 600; font-size: 0.8rem;
}
.agent-name-cell { color: #e2e8f0; font-weight: 500; font-size: 0.85rem; }
.badge {
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.04em;
}
.badge-seq  { background: #1a2a3a; color: #60a5fa; }
.badge-par  { background: #162516; color: #4ade80; }

/* ── Planning trace ── */
.trace-card {
    background: #161b27; border: 1px solid #1e2a3a;
    border-radius: 10px; padding: 1.25rem 1.5rem;
}
.trace-row { display: flex; gap: 0.75rem; margin-bottom: 0.75rem; align-items: flex-start; }
.trace-row:last-child { margin-bottom: 0; }
.trace-key {
    color: #4a6fa5; font-size: 0.72rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.08em;
    min-width: 140px; padding-top: 2px;
}
.trace-val { color: #c8d0db; font-size: 0.85rem; line-height: 1.5; }
.trace-val code {
    background: #1e2430; border-radius: 4px;
    padding: 1px 6px; font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem; color: #7dd3fc;
}
.competitor-chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.competitor-chip {
    background: #1e2430; border: 1px solid #2d3748;
    border-radius: 20px; padding: 2px 10px;
    color: #94a3b8; font-size: 0.78rem;
}

/* ── Agent timeline ── */
.timeline { display: flex; flex-direction: column; gap: 0; }
.timeline-item {
    display: flex; gap: 0; position: relative;
}
.tl-left {
    display: flex; flex-direction: column; align-items: center;
    width: 2.5rem; flex-shrink: 0;
}
.tl-dot {
    width: 28px; height: 28px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 700; flex-shrink: 0;
    border: 2px solid transparent; z-index: 1;
    transition: all 0.3s;
}
.tl-dot.idle    { background: #1a1f2e; border-color: #2d3748; color: #4a5568; }
.tl-dot.running { background: #1a2540; border-color: #4a6fa5; color: #60a5fa;
                  box-shadow: 0 0 12px rgba(74,111,165,0.4); }
.tl-dot.done    { background: #162516; border-color: #22c55e; color: #4ade80; }
.tl-dot.ok      { background: #162516; border-color: #22c55e; color: #4ade80; }
.tl-dot.error   { background: #2a1515; border-color: #ef4444; color: #f87171; }
.tl-dot.warning { background: #2a2015; border-color: #f59e0b; color: #fbbf24; }
.tl-dot.retry   { background: #2a2015; border-color: #f59e0b; color: #fbbf24; }

.tl-line {
    width: 2px; flex: 1; min-height: 1rem;
    background: linear-gradient(to bottom, #2d3748, #1e2430);
    margin: 2px 0;
}
.tl-content {
    flex: 1; padding: 0.1rem 0 1rem 1rem;
}
.tl-agent { color: #e2e8f0; font-weight: 600; font-size: 0.875rem; }
.tl-type   { color: #4a5568; font-size: 0.72rem; margin-left: 0.5rem; }
.tl-detail { color: #6b7280; font-size: 0.8rem; margin-top: 2px; }
.tl-detail.running { color: #60a5fa; }
.tl-detail.done    { color: #4ade80; }
.tl-detail.error   { color: #f87171; }

/* ── Log ── */
.log-wrap {
    background: #0e1117; border: 1px solid #1e2430; border-radius: 8px;
    padding: 0.75rem 1rem; max-height: 220px; overflow-y: auto;
    font-family: 'JetBrains Mono', monospace; font-size: 0.76rem;
    line-height: 1.65;
}
.log-line { display: flex; gap: 0.75rem; align-items: baseline; }
.log-time  { color: #374151; min-width: 52px; flex-shrink: 0; }
.log-badge {
    display: inline-block; min-width: 52px; text-align: center;
    border-radius: 3px; padding: 0 4px; font-size: 0.68rem;
    font-weight: 700; flex-shrink: 0;
}
.lb-tool   { background: #1a2a3a; color: #60a5fa; }
.lb-ok     { background: #162516; color: #4ade80; }
.lb-fail   { background: #2a1515; color: #f87171; }
.lb-rec    { background: #2a2015; color: #fbbf24; }
.lb-val    { background: #1e1a2e; color: #a78bfa; }
.lb-info   { background: #1a1f2e; color: #6b7280; }
.lb-conf-hi { background: #162516; color: #4ade80; }
.lb-conf-lo { background: #2a1f10; color: #f59e0b; }

/* ── Confidence score block ── */
.conf-block {
    background: #1a1f2e; border: 1px solid #2d3748;
    border-radius: 6px; padding: 0.5rem 0.75rem;
    margin: 2px 0 4px 0; display: flex; align-items: center; gap: 0.75rem;
}
.conf-label {
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.08em; white-space: nowrap;
}
.conf-label.high { color: #4ade80; }
.conf-label.low  { color: #f59e0b; }
.conf-bar-wrap {
    flex: 1; background: #111318; border-radius: 3px; height: 5px; overflow: hidden;
}
.conf-bar {
    height: 100%; border-radius: 3px;
    transition: width 0.4s;
}
.conf-bar.high { background: linear-gradient(90deg, #22c55e, #4ade80); }
.conf-bar.low  { background: linear-gradient(90deg, #d97706, #f59e0b); }
.conf-score { font-size: 0.72rem; color: #6b7280; white-space: nowrap; }
.conf-reason {
    font-size: 0.77rem; color: #64748b; font-style: italic;
    margin-top: 2px; line-height: 1.4;
}
.log-msg   { color: #8b9cb0; flex: 1; }
.log-msg b { color: #c8d0db; font-weight: 500; }
.log-details summary {
    cursor: pointer; display: inline-flex; align-items: center;
    list-style: none; color: #9aa3af; font-size: 0.72rem; margin-left: 6px;
}
.log-details summary::-webkit-details-marker { display: none; }
.log-details summary::before {
    content: '▶'; font-size: 0.5rem; color: #4a6fa5; margin-right: 4px;
}
.log-details[open] summary::before { content: '▼'; }
.log-details-content {
    margin-top: 4px; padding: 6px 10px; background: #161b27;
    border-left: 2px solid #4a6fa5; border-radius: 4px;
    font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
    color: #e2e8f0; white-space: pre-wrap; word-break: break-all;
}

/* ── Final report ── */
.report-card {
    background: #161b27; border: 1px solid #1e2430;
    border-radius: 10px; padding: 2rem 2.5rem;
}
.report-card h1, .report-card h2, .report-card h3 {
    color: #e2e8f0; border-bottom: 1px solid #1e2430; padding-bottom: 0.4rem;
}
.report-card li   { color: #9aa3af; }
.report-card strong { color: #c8d0db; }

/* ── Status banner ── */
.status-bar {
    display: flex; align-items: center; gap: 0.75rem;
    background: #161b27; border: 1px solid #1e2a3a;
    border-radius: 8px; padding: 0.65rem 1rem; margin-bottom: 1rem;
    font-size: 0.83rem;
}
.status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.status-dot.running { background: #60a5fa;
    box-shadow: 0 0 6px #60a5fa; animation: pulse 1.2s infinite; }
.status-dot.done    { background: #4ade80; }
.status-dot.idle    { background: #374151; }
@keyframes pulse {
  0%, 100% { opacity: 1; } 50% { opacity: 0.3; }
}

/* ── Meta strip ── */
.meta-strip {
    display: flex; gap: 1.5rem; flex-wrap: wrap;
    margin-bottom: 1rem; font-size: 0.8rem;
}
.meta-item { color: #4a5568; }
.meta-item span { color: #9aa3af; font-weight: 500; }

/* Streamlit element cleanup */
div[data-testid="stVerticalBlock"] > div:has(> div.element-container > div.stMarkdown > div > div.section-label) {
    margin-top: 0.5rem;
}
footer { display: none !important; }
#MainMenu { display: none !important; }
header { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────
DEFAULTS = {
    "running": False,
    "done": False,
    "plan_data": None,
    "agent_states": {},   # role → {status, detail, name, exec_type}
    "log_lines": [],      # list of {time, badge_cls, badge, msg}
    "report": "",
    "final_meta": {},
    "thread_result": {},
    "log_counter": 0,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# Background runner
# ─────────────────────────────────────────────────────────────────────────────
def _run_graph(company: str, result_holder: dict):
    from competitive_intel import ui_callback as cb
    from competitive_intel.graph import graph
    cb.activate()
    t0 = time.time()
    try:
        state = {
            "company_name": company, "sector": "", "competitors": [],
            "research_results": [], "retry_count": 0, "missing_sections": [],
            "should_retry": False, "final_report": "",
            "planning_trace": [], "error_log": [],
        }
        final = graph.invoke(state, config={"max_concurrency": 4})
        result_holder.update({"state": final, "elapsed": time.time() - t0, "error": None})
    except Exception as exc:
        result_holder.update({"state": {}, "elapsed": time.time() - t0, "error": str(exc)})
    finally:
        cb.deactivate()

# ─────────────────────────────────────────────────────────────────────────────
# Agent order definition
# ─────────────────────────────────────────────────────────────────────────────
AGENT_ORDER = [
    ("orchestrator",     "Orchestrator",       "Sequential — Phase 1"),
    ("product_agent",    "Product Agent",       "Parallel — Phase 2"),
    ("reputation_agent", "Sentiment Agent",     "Parallel — Phase 2"),
    ("news_agent",       "News Agent",          "Parallel — Phase 2"),
]

TOOL_LABEL = {
    "tool_call":  ("lb-tool", "CALL"),
    "tool_ok":    ("lb-ok",   "OK"),
    "tool_fail":  ("lb-fail", "FAIL"),
    "tool_recovery": ("lb-rec", "RETRY"),
    "validate":   ("lb-val",  "VALID"),
    "confidence": ("lb-conf-hi", "CONF"),   # badge class overridden at render time
    "fanin":      ("lb-info", "FAN-IN"),
    "synthesis_start": ("lb-info", "SYNTH"),
    "synthesis_done":  ("lb-ok",   "DONE"),
    "done":            ("lb-ok",   "DONE"),
    "error":           ("lb-fail", "ERR"),
}

PRIORITY = {"idle": 0, "running": 1, "warning": 2, "retry": 2, "ok": 3, "done": 4, "error": 4}

# ─────────────────────────────────────────────────────────────────────────────
# Process events → session state
# ─────────────────────────────────────────────────────────────────────────────
def process_events(events: list):
    elapsed_base = time.time()
    for ev in events:
        t = ev["type"]
        agent = ev["agent"]
        data = ev.get("data", {})

        # Skip token noise
        if t == "synthesis_token":
            st.session_state.report += data.get("token", "")
            continue

        # Update agent states
        if t == "step":
            status = data.get("status", "running")
            existing = st.session_state.agent_states.get(agent, {})
            if PRIORITY.get(status, 0) >= PRIORITY.get(existing.get("status", "idle"), 0):
                st.session_state.agent_states[agent] = {
                    "status": status,
                    "detail": data.get("detail", ""),
                    "name": data.get("step", agent),
                }

        if t == "plan":
            st.session_state.plan_data = data

        # Build clean log line
        badge_cls, badge = TOOL_LABEL.get(t, ("lb-info", "INFO"))

        if t == "tool_call":
            tool = data.get("tool", "")
            full_args = data.get("args_preview", "")
            if len(full_args) > 50:
                short = full_args[:50] + "..."
                msg = (f'<b>{tool}</b>'
                       f'<details class="log-details">'
                       f'<summary>({short})</summary>'
                       f'<div class="log-details-content">{full_args}</div>'
                       f'</details>')
            else:
                msg = f"<b>{tool}</b>({full_args})"
        elif t == "tool_ok":
            msg = f"<b>Success</b> — {ev['message'][:80]}"
        elif t == "tool_fail":
            msg = f"<b>Failure</b> — {data.get('error','')[:80]}"
        elif t == "tool_recovery":
            query = data.get("query", "")
            if len(query) > 50:
                short = query[:50] + "..."
                msg = (f'<b>Fallback query:</b> '
                       f'<details class="log-details">'
                       f'<summary>{short}</summary>'
                       f'<div class="log-details-content">{query}</div>'
                       f'</details>')
            else:
                msg = f"<b>Fallback query:</b> {query}"
        elif t == "validate":
            ok = data.get("valid", False)
            errs = data.get("errors", [])
            msg = f"<b>Schema valid</b> ✓" if ok else f"<b>Schema invalid</b> — {errs}"
        elif t == "fanin":
            msg = "<b>All parallel agents finished</b> — proceeding to synthesis"
        elif t == "synthesis_start":
            msg = "<b>Generating final report</b>..."
        elif t == "synthesis_done":
            msg = f"<b>Report complete</b> — {data.get('chars',0)} characters"
        elif t == "done":
            msg = "<b>Pipeline finished successfully</b>"
        elif t == "error":
            msg = f"<b>Unhandled error:</b> {data.get('error','')[:80]}"
        elif t == "step":
            continue  # shown in timeline, skip log
        elif t == "confidence":
            score = data.get("score", 5)
            reason = data.get("reason", "")
            low = data.get("low", False)
            cls_str  = "low" if low else "high"
            badge_cls = "lb-conf-lo" if low else "lb-conf-hi"
            badge = "CONF"
            action = "Low confidence — fallback search triggered" if low else "High confidence — proceeding"
            pct = int((score / 10) * 100)
            msg = (
                f'<span style="color:{"#f59e0b" if low else "#4ade80"}">'  
                f'<b>Score {score}/10</b></span> — {action}'  
                f'<div class="conf-block">'  
                f'<span class="conf-label {cls_str}">CONFIDENCE</span>'  
                f'<div class="conf-bar-wrap"><div class="conf-bar {cls_str}" style="width:{pct}%"></div></div>'  
                f'<span class="conf-score">{score}/10</span>'  
                f'</div>'  
                f'<div class="conf-reason">LLM reasoning: {reason[:120]}</div>'
            )
            ts = time.strftime("%H:%M:%S")
            st.session_state.log_lines.append({
                "ts": ts, "cls": badge_cls, "badge": badge,
                "agent": agent.replace("_agent","").replace("_"," ").title(),
                "msg": msg,
            })
            continue
        elif t == "findings":
            continue  # skip raw findings preview
        else:
            msg = ev["message"][:90]

        ts = time.strftime("%H:%M:%S")
        st.session_state.log_lines.append({
            "ts": ts, "cls": badge_cls, "badge": badge,
            "agent": agent.replace("_agent","").replace("_"," ").title(),
            "msg": msg,
        })

# ─────────────────────────────────────────────────────────────────────────────
# Render helpers
# ─────────────────────────────────────────────────────────────────────────────
def dot_icon(status: str) -> str:
    icons = {"idle": "·", "running": "⋯", "done": "✓",
             "ok": "✓", "error": "✗", "warning": "!", "retry": "↺"}
    return icons.get(status, "·")

def render_timeline():
    html = '<div class="timeline">'
    for i, (role, label, exec_type) in enumerate(AGENT_ORDER):
        info = st.session_state.agent_states.get(role, {})
        status = info.get("status", "idle")
        detail = info.get("detail", "Waiting...")
        last = (i == len(AGENT_ORDER) - 1)

        detail_display = detail[:80] if detail else "Waiting..."
        detail_cls = status if status in ("running", "done", "error") else ""

        html += f"""
        <div class="timeline-item">
          <div class="tl-left">
            <div class="tl-dot {status}">{dot_icon(status)}</div>
            {"" if last else '<div class="tl-line"></div>'}
          </div>
          <div class="tl-content">
            <span class="tl-agent">{label}</span>
            <span class="tl-type">{exec_type}</span>
            <div class="tl-detail {detail_cls}">{detail_display}</div>
          </div>
        </div>"""
    html += "</div>"
    return html

def render_log():
    if not st.session_state.log_lines:
        return '<div class="log-wrap"><span style="color:#374151">Waiting for activity...</span></div>'
    rows = ""
    for ln in st.session_state.log_lines[-40:]:  # last 40 entries
        rows += (
            f'<div class="log-line">'
            f'<span class="log-time">{ln["ts"]}</span>'
            f'<span class="log-badge {ln["cls"]}">{ln["badge"]}</span>'
            f'<span class="log-msg">{ln["msg"]}</span>'
            f'</div>'
        )
    return f'<div class="log-wrap">{rows}</div>'

def render_plan(plan: dict):
    hypothesis = plan.get("hypothesis_sector", "—")
    intent     = plan.get("search_intent", "—")
    comps      = plan.get("expected_competitors", [])
    chips = "".join(f'<span class="competitor-chip">{c}</span>' for c in comps)

    return f"""<div class="trace-card">
  <div class="trace-row">
    <span class="trace-key">Hypothesis</span>
    <span class="trace-val">{hypothesis}</span>
  </div>
  <div class="trace-row">
    <span class="trace-key">Search intent</span>
    <span class="trace-val">{intent}</span>
  </div>
  <div class="trace-row">
    <span class="trace-key">Expected rivals</span>
    <span class="trace-val"><div class="competitor-chips">{chips if chips else "—"}</div></span>
  </div>
</div>"""

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
  <div class="app-title"> CompIntel</div>
  <div class="app-subtitle">Multi-agent competitive intelligence · powered by LangGraph, Groq &amp; Tavily</div>
  <div class="tech-pills">
    <span class="pill">LangGraph</span>
    <span class="pill">Groq gpt-oss-120b</span>
    <span class="pill">Tavily Search</span>
    <span class="pill">Pydantic Validation</span>
    <span class="pill">Fan-Out / Fan-In</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# INPUT ROW
# ─────────────────────────────────────────────────────────────────────────────
col_in, col_btn = st.columns([5, 1])
with col_in:
    company = st.text_input("company", placeholder='Enter a company name — e.g. "Notion", "Stripe", "OpenAI"',
                            label_visibility="collapsed", key="company_input")
with col_btn:
    run_clicked = st.button("▶  Analyse", use_container_width=True,
                            disabled=st.session_state.running)

# ─────────────────────────────────────────────────────────────────────────────
# EXECUTION PLAN (always visible)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Execution Plan</div>', unsafe_allow_html=True)

rows_html = ""
for step_n, agent_n, exec_t, tool_desc, btype in [
    ("1",   "Orchestrator",      "Sequential",  "Planning trace → web search → sector/competitor extraction",           "seq"),
    ("2a",  "Product Agent",     "Parallel",    "Dynamic sector-aware search — core technology and capabilities",       "par"),
    ("2b",  "Sentiment Agent",   "Parallel",    "Employee reviews — Glassdoor, Indeed, AmbitionBox",                   "par"),
    ("2c",  "News Agent",        "Parallel",    "Web search — news and strategic moves",                         "par"),
    ("3",   "Synthesis Guard",   "Sequential",  "Quality check → LLM synthesis → final report",                        "seq"),
]:
    bc = "badge-seq" if btype == "seq" else "badge-par"
    rows_html += f"""
    <tr>
      <td><span class="step-num">{step_n}</span></td>
      <td><span class="agent-name-cell">{agent_n}</span></td>
      <td><span class="badge {bc}">{exec_t}</span></td>
      <td>{tool_desc}</td>
    </tr>"""

st.markdown(f"""
<table class="plan-table">
  <thead>
    <tr><th style="width:40px">#</th><th style="width:160px">Agent</th><th style="width:110px">Mode</th><th>What it does</th></tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TRIGGER RUN
# ─────────────────────────────────────────────────────────────────────────────
if run_clicked and company.strip():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    st.session_state.running = True
    result_holder = {}
    st.session_state.thread_result = result_holder
    threading.Thread(target=_run_graph, args=(company.strip(), result_holder), daemon=True).start()
    st.rerun()
elif run_clicked:
    st.warning("Please enter a company name.")

# ─────────────────────────────────────────────────────────────────────────────
# LIVE / RESULTS PANEL
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.running or st.session_state.done:

    # Drain event queue
    if st.session_state.running:
        from competitive_intel import ui_callback as cb
        new_events = cb.drain()
        if new_events:
            process_events(new_events)

        # Check if thread finished
        res = st.session_state.thread_result
        if res.get("state") is not None or res.get("error") is not None:
            if not st.session_state.report:
                st.session_state.report = res.get("state", {}).get("final_report", "")
            st.session_state.final_meta = {
                "sector":      res.get("state", {}).get("sector", ""),
                "competitors": res.get("state", {}).get("competitors", []),
                "retry_count": res.get("state", {}).get("retry_count", 0),
                "elapsed":     round(res.get("elapsed", 0), 1),
                "error":       res.get("error"),
            }
            st.session_state.running = False
            st.session_state.done = True

    # ── Status bar ────────────────────────────────────────────────────────────
    # Show company name being analyzed
    target_co = company.strip() if company.strip() else "—"
    if st.session_state.running:
        status_dot = "running"
        status_text = f'Analysing <b style="color:#e2e8f0">{target_co}</b> … this takes about 20–40 seconds'
    elif st.session_state.done and not st.session_state.final_meta.get("error"):
        elapsed = st.session_state.final_meta.get("elapsed", 0)
        status_dot = "done"
        status_text = f'Analysis of <b style="color:#e2e8f0">{target_co}</b> complete in {elapsed}s'
    else:
        status_dot = "done"
        status_text = f"Error: {st.session_state.final_meta.get('error','Unknown')}"

    st.markdown(f"""
    <div class="status-bar">
      <div class="status-dot {status_dot}"></div>
      <span style="color:#9aa3af">{status_text}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Activity Log (full width) ─────────────────────────────────────────
    st.markdown('<div class="section-label">Activity Log</div>', unsafe_allow_html=True)
    st.markdown(render_log(), unsafe_allow_html=True)

    # ── Planning trace ────────────────────────────────────────────────────
    if st.session_state.plan_data:
        st.markdown('<div class="section-label">Orchestrator Planning Trace</div>', unsafe_allow_html=True)
        st.markdown(render_plan(st.session_state.plan_data), unsafe_allow_html=True)
    elif st.session_state.running:
        st.markdown(
            '<p style="color:#374151;font-size:0.83rem;margin-top:1rem">'
            'Waiting for the Orchestrator to produce its planning trace…</p>',
            unsafe_allow_html=True,
        )

    # ── Final report ──────────────────────────────────────────────────────
    if st.session_state.report:
        st.markdown('<div class="section-label">Competitive Intelligence Brief</div>',
                    unsafe_allow_html=True)

        meta = st.session_state.final_meta
        if meta.get("sector"):
            comps_str = ", ".join(meta.get("competitors", [])) or "—"
            hq_str = meta.get("headquarters", "Unknown")
            st.markdown(
                f'<div class="meta-strip">'
                f'<div class="meta-item">Sector <span>{meta["sector"]}</span></div>'
                f'<div class="meta-item">HQ <span>{hq_str}</span></div>'
                f'<div class="meta-item">Rivals identified <span>{comps_str}</span></div>'
                f'<div class="meta-item">Retries <span>{meta.get("retry_count",0)}</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        col_rep, col_dl = st.columns([6, 1])
        with col_dl:
            if st.session_state.done:
                nm = st.session_state.get("company_input", "company").lower().replace(" ","_")
                st.download_button("⬇ .md", data=st.session_state.report,
                                   file_name=f"brief_{nm}.md", mime="text/markdown")

        # Render report as proper markdown (no wrapping div trick)
        st.markdown(st.session_state.report)

    # ── Auto-rerun ────────────────────────────────────────────────────────
    if st.session_state.running:
        time.sleep(0.4)
        st.rerun()
