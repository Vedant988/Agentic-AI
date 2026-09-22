"""
competitive_intel/agents/synthesis_agent.py
--------------------------------------------
STEP 3 — Sequential

The Synthesis & Quality Guard:
  1. Receives all research_results from the fan-in
  2. Checks for missing/thin sections (self-correction gate)
  3. Calls Groq (streaming) to produce the final markdown brief
  4. Returns the final_report to state

Self-correction: if any section has < 30 chars of findings, it sets
should_retry=True so the graph can loop back (up to retry_count=2).
"""

import json
from rich.console import Console

from competitive_intel.llm import call_llm, call_llm_streaming
from competitive_intel.state import OverallState
from competitive_intel import ui_callback as cb

console = Console()

REQUIRED_SECTIONS = ["product_agent", "reputation_agent", "news_agent"]
MIN_FINDINGS_LEN = 30


def synthesis_node(state: OverallState) -> dict:
    company = state["company_name"]
    sector = state.get("sector", "Unknown")
    competitors = state.get("competitors", [])
    research_results = state.get("research_results", [])
    retry_count = state.get("retry_count", 0)
    error_log = state.get("error_log", [])

    console.rule("[bold blue]🔬 SYNTHESIS AGENT — Quality Check & Report Generation")

    # ── QUALITY CHECK ─────────────────────────────────────────────────────────
    present_roles = {r.get("agent_role", "") for r in research_results}
    missing_sections = []
    thin_sections = []

    for role in REQUIRED_SECTIONS:
        section_data = next((r for r in research_results if r.get("agent_role") == role), None)
        if section_data is None:
            missing_sections.append(role)
            console.print(f"[bold red]X Missing section:[/bold red] {role}")
            cb.emit("step", "synthesis", f"Section missing: {role}", {
                "step": role, "status": "error", "detail": "No data received",
            })
        elif len(section_data.get("findings", "")) < MIN_FINDINGS_LEN:
            thin_sections.append(role)
            console.print(f"[yellow]^ Thin section:[/yellow] {role}")
            cb.emit("step", "synthesis", f"Section thin: {role}", {
                "step": role, "status": "warning", "detail": "Findings too short",
            })
        else:
            console.print(f"[green]OK Section:[/green] {role}")
            cb.emit("step", "synthesis", f"Section OK: {role}", {
                "step": role, "status": "ok", "detail": "Findings sufficient",
            })

    # ── RETRY DECISION ────────────────────────────────────────────────────────
    if (missing_sections or thin_sections) and retry_count < 2:
        console.print(f"[yellow]Retrying #{retry_count + 1}...[/yellow]")
        cb.emit("step", "synthesis", f"Quality check failed — retry #{retry_count+1}", {
            "step": "Synthesis & Quality Guard", "status": "retry",
            "detail": f"Missing: {missing_sections}, Thin: {thin_sections}",
        })
        return {
            "should_retry": True,
            "missing_sections": missing_sections + thin_sections,
            "retry_count": retry_count + 1,
            "final_report": "",
        }

    if missing_sections or thin_sections:
        console.print(f"[yellow]^ Max retries reached. Proceeding.[/yellow]")

    # ── BUILD CONTEXT FOR LLM (token-budget aware) ───────────────────────────
    # Groq free tier: 8000 TPM max. We truncate aggressively to stay under.
    MAX_FINDINGS_CHARS = 600  # per section
    sections_text = ""
    for role in REQUIRED_SECTIONS:
        section_data = next((r for r in research_results if r.get("agent_role") == role), None)
        if section_data:
            label = role.replace("_agent", "").replace("_", " ").title()
            findings = section_data.get("findings", "No data available.")[:MAX_FINDINGS_CHARS]
            sources = section_data.get("sources", [])[:2]
            source_list = "\n".join(f"  - {s}" for s in sources)
            sections_text += f"\n### {label}\n{findings}\n\nSources:\n{source_list}\n"

    errors_summary = ""
    if error_log:
        errors_summary = "\n\nNOTE — Tool errors occurred (recovered):\n"
        errors_summary += "\n".join(f"  - {e}" for e in error_log[:3])

    synthesis_prompt = [
        {
            "role": "system",
            "content": (
                "You are an executive briefer. Your job is to take raw research data "
                "and distill it into a hyper-concise, highly readable summary. "
                "DO NOT produce long AI-like essays. DO NOT list every possible detail. "
                "Be extremely brief, punchy, and highlight ONLY the most critical, high-impact facts. "
                "Use short bullet points. Cut the fluff."
            ),
        },
        {
            "role": "user",
            "content": (
                f"# Executive Brief\n\n"
                f"**Target Company:** {company}\n"
                f"**Sector:** {sector}\n"
                f"**Key Competitors:** {', '.join(competitors)}\n"
                f"{errors_summary}\n\n"
                f"## Research Data\n{sections_text}\n\n"
                "Produce a short, easily readable Markdown brief with these sections (max 2-3 bullets per section):\n"
                "1. Executive Summary (1 paragraph max)\n"
                "2. Product & Technology (core capabilities and competitive edge)\n"
                "3. Employee & Workplace Sentiment (top praise, top complaint)\n"
                "4. Recent News & Momentum (only major strategic developments)\n"
                "Keep the entire report under 350 words."
            ),
        },
    ]

    # ── STREAMING OUTPUT (with rate-limit fallback) ───────────────────────────
    console.rule("[bold blue]>> Generating Final Report (streaming...)")
    cb.emit("synthesis_start", "synthesis", "Synthesis streaming started", {})
    cb.emit("step", "synthesis", "Synthesis — generating report", {
        "step": "Synthesis & Quality Guard", "status": "running",
        "detail": "Streaming final competitive-landscape brief...",
    })
    report_chunks = []

    try:
        for token in call_llm_streaming(synthesis_prompt, reasoning_effort="medium"):
            print(token, end="", flush=True)
            report_chunks.append(token)
            cb.emit("synthesis_token", "synthesis", token, {"token": token})
        print()  # newline after stream
        cb.emit("synthesis_done", "synthesis", "Streaming complete", {
            "chars": sum(len(c) for c in report_chunks),
        })

    except Exception as exc:
        # Groq 413 rate-limit or any other API error — fallback to non-streaming
        # with a more compact prompt
        err_str = str(exc)
        console.print(f"\n[bold red]>> Streaming failed:[/bold red] {err_str[:120]}")
        console.print("[yellow]>> Fallback: non-streaming synthesis with compact prompt...[/yellow]")

        compact_prompt = [
            {
                "role": "system",
                "content": "You are an executive briefer. Write a hyper-concise, human-readable competitive brief. No fluff.",
            },
            {
                "role": "user",
                "content": (
                    f"Company: {company} | Sector: {sector} | Competitors: {', '.join(competitors)}\n\n"
                    f"{sections_text[:1800]}\n\n"
                    "Write a very short, punchy Markdown brief (under 250 words total). "
                    "Use maximum 2 bullets per section for: Products, Pricing, Reputation, and Recent News."
                ),
            },
        ]
        try:
            final_report = call_llm(compact_prompt, reasoning_effort="medium")
            console.print("[green]>> Fallback synthesis succeeded.[/green]")
        except Exception as fallback_exc:
            # Ultimate graceful degradation — assemble from raw findings
            console.print(f"[red]>> Fallback also failed: {fallback_exc}[/red]")
            console.print("[yellow]>> Assembling report from raw agent findings...[/yellow]")
            final_report = f"# Competitive Intelligence Report: {company}\n\n"
            final_report += f"**Sector:** {sector}\n**Competitors:** {', '.join(competitors)}\n\n"
            for role in REQUIRED_SECTIONS:
                section_data = next(
                    (r for r in research_results if r.get("agent_role") == role), None
                )
                if section_data:
                    label = role.replace("_agent", "").replace("_", " ").title()
                    final_report += f"\n## {label}\n{section_data.get('findings', '')}\n"
            return {
                "final_report": final_report,
                "should_retry": False,
                "missing_sections": [],
                "error_log": [f"[synthesis] Streaming: {err_str[:80]}. Fallback: {str(fallback_exc)[:80]}"],
            }

        report_chunks = [final_report]

    final_report = "".join(report_chunks)

    console.print(f"\n[bold green]>> Report generated:[/bold green] {len(final_report)} chars")
    cb.emit("step", "synthesis", "Synthesis — complete", {
        "step": "Synthesis & Quality Guard", "status": "done",
        "detail": f"{len(final_report)} characters generated",
    })
    cb.emit("done", "synthesis", "Pipeline complete", {
        "chars": len(final_report), "sector": sector, "competitors": competitors,
    })

    return {
        "final_report": final_report,
        "should_retry": False,
        "missing_sections": [],
        "error_log": [],
    }

