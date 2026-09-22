"""
competitive_intel/agents/orchestrator.py
-----------------------------------------
STEP 1 — Sequential

Phases:
  1. PLAN  — Groq produces a JSON planning trace (emitted to UI)
  2. ACT   — tavily_search for sector + competitors
  3. EXTRACT — LLM parses results → pydantic_json_validator
"""

import json
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from competitive_intel.llm import call_llm
from competitive_intel.tools import tavily_search, pydantic_json_validator
from competitive_intel.state import OverallState
from competitive_intel import ui_callback as cb

console = Console()


def orchestrator_node(state: OverallState) -> dict:
    company = state["company_name"]

    # ── PHASE 1: PLAN ─────────────────────────────────────────────────────────
    console.rule("[bold cyan]>> ORCHESTRATOR — Phase 1: PLANNING TRACE")
    cb.emit("step", "orchestrator", "Orchestrator — generating plan", {
        "step": "Orchestrator", "status": "running",
        "detail": f"Producing JSON planning trace for: {company}",
    })

    plan_prompt = [
        {
            "role": "system",
            "content": (
                "You are the Orchestrator of a competitive intelligence system. "
                "Before taking any action, produce a concise JSON planning trace. "
                "Output ONLY valid JSON, no markdown fences."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Target company: {company}\n\n"
                "Produce a JSON planning trace with these exact keys:\n"
                "{\n"
                '  "target_company": "<name>",\n'
                '  "hypothesis_sector": "<your initial sector guess>",\n'
                '  "search_intent": "<what you are trying to confirm with web search>",\n'
                '  "expected_competitors": ["<comp1>", "<comp2>", "<comp3>"]\n'
                "}"
            ),
        },
    ]

    plan_json_str = call_llm(plan_prompt, reasoning_effort="medium")

    try:
        plan_data = json.loads(plan_json_str.strip())
    except json.JSONDecodeError:
        plan_data = {"raw": plan_json_str.strip()}

    console.print(Panel(
        Syntax(json.dumps(plan_data, indent=2), "json", theme="monokai", word_wrap=True),
        title="[bold green]>> Planning Trace",
        border_style="green",
    ))

    # Emit the plan to UI
    cb.emit("plan", "orchestrator", "Planning trace generated", plan_data)

    # ── PHASE 2: ACT ──────────────────────────────────────────────────────────
    console.rule("[bold cyan]>> ORCHESTRATOR — Phase 2: SEARCH")
    query = f'"{company}" market sector competitors overview'
    cb.emit("tool_call", "orchestrator", f"tavily_search(query={query!r})", {
        "tool": "tavily_search", "args_preview": f"query={query!r}, max_results=7",
    })

    search_result = tavily_search(query=query, max_results=7, search_depth="advanced")

    if not search_result["success"]:
        err_msg = f"Orchestrator tavily_search failed: {search_result['error']}"
        cb.emit("tool_fail", "orchestrator", err_msg, {
            "error": err_msg, "recovery": "Retrying with shorter query",
        })
        fallback_query = f"{company} competitors"
        cb.emit("tool_recovery", "orchestrator", f"Fallback: {fallback_query!r}", {
            "query": fallback_query,
        })
        search_result = tavily_search(query=fallback_query, max_results=5)
        if not search_result["success"]:
            cb.emit("step", "orchestrator", "Orchestrator — failed", {
                "step": "Orchestrator", "status": "error",
                "detail": f"Both searches failed: {search_result['error']}",
            })
            return {
                "sector": "Unknown", "competitors": [],
                "planning_trace": [f"[ORCHESTRATOR] Plan:\n{plan_json_str}"],
                "error_log": [err_msg],
            }

    cb.emit("tool_ok", "orchestrator", f"{len(search_result['results'])} results", {
        "result_preview": f"Top: {search_result['results'][0]['title'][:60] if search_result['results'] else 'N/A'}",
    })

    snippets = [r["content"][:300] for r in search_result["results"][:5]]

    # ── PHASE 3: EXTRACT ──────────────────────────────────────────────────────
    console.rule("[bold cyan]>> ORCHESTRATOR — Phase 3: EXTRACT")
    cb.emit("step", "orchestrator", "Orchestrator — extracting sector + competitors", {
        "step": "Orchestrator", "status": "running",
        "detail": "Calling LLM to parse sector and competitors from search results",
    })

    extract_prompt = [
        {
            "role": "system",
            "content": (
                "You are a structured data extractor. From web search snippets about a company, "
                "extract its market sector, its top 3 direct competitors, its headquarters location (city/country), and a brief 1-2 sentence "
                "summary of what the company actually does (its core business model and products). "
                "Output ONLY valid JSON with keys: sector (string), headquarters (string), competitors (array of 3 strings), "
                "company_summary (string). No markdown, no explanation."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Company: {company}\n\nSearch snippets:\n" + "\n---\n".join(snippets) +
                "\n\nExtract sector, headquarters, top 3 competitors, and company_summary as JSON."
            ),
        },
    ]

    extract_json_str = call_llm(extract_prompt)

    cb.emit("tool_call", "orchestrator", "pydantic_json_validator(schema='OrchestratorOutput')", {
        "tool": "pydantic_json_validator", "args_preview": "schema=OrchestratorOutput",
    })
    validation = pydantic_json_validator(extract_json_str.strip(), "OrchestratorOutput")

    if not validation["valid"]:
        cb.emit("tool_fail", "orchestrator", f"Validation failed: {validation['errors']}", {
            "error": str(validation["errors"]),
            "recovery": "Re-prompting LLM with error context",
        })
        correction_prompt = extract_prompt + [
            {"role": "assistant", "content": extract_json_str},
            {
                "role": "user",
                "content": (
                    f"Your JSON failed: {validation['errors']}\n"
                    "Fix it: sector (string), headquarters (string), competitors (array of 3 strings), company_summary (string)."
                ),
            },
        ]
        extract_json_str = call_llm(correction_prompt)
        validation = pydantic_json_validator(extract_json_str.strip(), "OrchestratorOutput")
        cb.emit("tool_ok", "orchestrator", f"Re-validation: valid={validation['valid']}", {
            "result_preview": f"valid={validation['valid']}",
        })

    if validation["valid"] and validation["data"]:
        sector = validation["data"]["sector"]
        headquarters = validation["data"]["headquarters"]
        competitors = validation["data"]["competitors"]
        company_summary = validation["data"]["company_summary"]
    else:
        try:
            raw = json.loads(extract_json_str.strip())
            sector = raw.get("sector", "Technology")
            headquarters = raw.get("headquarters", "Unknown")
            competitors = raw.get("competitors", [])[:3]
            company_summary = raw.get("company_summary", f"{company} is a business in the {sector} sector.")
        except Exception:
            sector = "Technology"
            headquarters = "Unknown"
            competitors = []
            company_summary = f"{company} is a business in the {sector} sector."

    cb.emit("validate", "orchestrator", f"Pydantic valid={validation['valid']}", {
        "valid": validation["valid"], "errors": validation.get("errors", []),
    })
    cb.emit("step", "orchestrator", "Orchestrator — complete", {
        "step": "Orchestrator",
        "status": "done",
        "detail": f"Sector: {sector} | Rivals: {', '.join(competitors)}",
    })

    console.print(f"[bold green]>> Sector:[/bold green] {sector}")
    console.print(f"[bold green]>> HQ:[/bold green] {headquarters}")
    console.print(f"[bold green]>> Competitors:[/bold green] {competitors}")
    console.print(f"[bold green]>> Summary:[/bold green] {company_summary}")

    return {
        "sector": sector,
        "headquarters": headquarters,
        "competitors": competitors,
        "company_summary": company_summary,
        "planning_trace": [
            f"[ORCHESTRATOR] Plan:\n{json.dumps(plan_data, indent=2)}\n"
            f"→ sector: {sector} | HQ: {headquarters} | competitors: {competitors}\n"
            f"→ summary: {company_summary}"
        ],
        "error_log": [],
    }
