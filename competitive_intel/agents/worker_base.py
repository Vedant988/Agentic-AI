"""
competitive_intel/agents/worker_base.py
----------------------------------------
Shared base logic for all 4 parallel worker agents.

Flow:
  1. Planning trace
  2. Tavily search (with TimeoutError recovery)
  3. Deterministic data-quality check (result count + snippet volume)
     If data is thin → trigger wider fallback search (no LLM reasoning)
  4. LLM synthesis on final snippets
  5. Pydantic validation
"""

import json
from rich.console import Console

from competitive_intel.llm import call_llm
from competitive_intel.tools import tavily_search, pydantic_json_validator
from competitive_intel import ui_callback as cb

console = Console()

# ── Deterministic thresholds ─────────────────────────────────────────────────
MIN_RESULTS = 3              # fewer results than this = low data
MIN_SNIPPET_CHARS = 500      # total snippet text shorter than this = thin data


def run_worker(
    agent_role: str,
    company_name: str,
    sector: str,
    competitors: list[str],
    search_kwargs: dict,
    system_prompt: str,
    user_prompt_template: str,
    simulate_failure: bool = False,
) -> dict:
    competitor_str = ", ".join(competitors) if competitors else "N/A"
    agent_label = agent_role.upper().replace("_", " ")
    topic = agent_role.replace("_agent", "").replace("_", " ")

    # ── PLANNING TRACE ────────────────────────────────────────────────────────
    console.rule(f"[bold magenta]>> {agent_label} — Planning Trace")
    plan_detail = (
        f"Target: {company_name} | Sector: {sector}\n"
        f"Competitors: {competitor_str}\n"
        f"Search config: {json.dumps(search_kwargs, indent=2)}"
    )
    console.print(f"[dim cyan]{plan_detail}[/dim cyan]")

    cb.emit("step", agent_role, f"{agent_label} — planning", {
        "step": agent_label,
        "status": "running",
        "detail": f"Planning search for {topic} intelligence",
    })

    # ── TAVILY SEARCH ─────────────────────────────────────────────────────────
    query = search_kwargs.pop("query")
    console.print(f"[yellow]→ Tool call:[/yellow] tavily_search(query={query!r})")

    cb.emit("tool_call", agent_role, f"tavily_search(query={query!r})", {
        "tool": "tavily_search",
        "args_preview": f"query={query!r}, {search_kwargs}",
    })

    try:
        search_result = tavily_search(
            query=query,
            simulate_failure=simulate_failure,
            **search_kwargs,
        )
    except TimeoutError as exc:
        err_str = str(exc)
        console.print(f"\n[bold red]>> TOOL FAILURE:[/bold red] {err_str}")
        cb.emit("tool_fail", agent_role, "Tavily TimeoutError", {
            "error": err_str,
            "recovery": "Retrying with simplified query",
        })

        fallback_kwargs = {k: v for k, v in search_kwargs.items()
                          if k not in ("time_range", "include_domains")}
        fallback_query = f"{company_name} {competitors[0] if competitors else ''} {topic}"
        cb.emit("tool_recovery", agent_role, f"Fallback query: {fallback_query!r}", {
            "query": fallback_query,
        })
        search_result = tavily_search(query=fallback_query, **fallback_kwargs)

        if search_result["success"]:
            cb.emit("tool_ok", agent_role, f"Recovery OK — {len(search_result['results'])} results", {
                "result_preview": f"{len(search_result['results'])} results from fallback",
            })
        else:
            cb.emit("tool_fail", agent_role, f"Recovery failed: {search_result['error']}", {
                "error": search_result["error"], "recovery": "N/A",
            })
            return {
                "research_results": [{
                    "agent_role": agent_role, "company": company_name,
                    "findings": "Data unavailable — both primary and fallback searches failed.",
                    "sources": [], "raw_snippets": [],
                }],
                "error_log": [f"[{agent_role}] TimeoutError + fallback failed: {search_result['error']}"],
            }

    if not search_result["success"]:
        err = search_result["error"]
        cb.emit("tool_fail", agent_role, err, {"error": err, "recovery": "N/A"})
        return {
            "research_results": [{
                "agent_role": agent_role, "company": company_name,
                "findings": f"Search failed: {err}", "sources": [], "raw_snippets": [],
            }],
            "error_log": [f"[{agent_role}] {err}"],
        }

    results = search_result["results"]
    snippets = [f"[{r['title']}] {r['content'][:400]}" for r in results[:5]]
    sources = [r["url"] for r in results]

    cb.emit("tool_ok", agent_role, f"{len(results)} results retrieved", {
        "result_preview": f"Top: {results[0]['title'][:60] if results else 'N/A'}",
    })

    # ── DETERMINISTIC DATA-QUALITY CHECK ──────────────────────────────────────
    # No LLM reasoning here — pure metrics: result count + total snippet volume.
    total_chars = sum(len(s) for s in snippets)
    is_thin = len(results) < MIN_RESULTS or total_chars < MIN_SNIPPET_CHARS

    if is_thin:
        reason = (f"{len(results)} results, {total_chars} chars "
                  f"(thresholds: {MIN_RESULTS} results, {MIN_SNIPPET_CHARS} chars)")
        console.print(f"[yellow]>> Thin data detected: {reason}. Triggering fallback.[/yellow]")
        cb.emit("confidence", agent_role, f"Thin data — {reason}", {
            "score": min(len(results), 4),
            "max": 10,
            "threshold": 5,
            "reason": f"Deterministic check: {reason}",
            "low": True,
        })
        cb.emit("tool_recovery", agent_role, "Thin data — broader fallback search", {
            "query": f"{company_name} {topic} overview",
        })

        fallback_kwargs = {k: v for k, v in search_kwargs.items()
                          if k not in ("time_range", "include_domains")}
        fallback_query = f"{company_name} {topic} overview analysis"
        fallback_result = tavily_search(query=fallback_query, max_results=7, **fallback_kwargs)

        if fallback_result["success"] and fallback_result["results"]:
            results = fallback_result["results"]
            snippets = [f"[{r['title']}] {r['content'][:400]}" for r in results[:5]]
            sources = [r["url"] for r in results]
            console.print(f"[green]>> Fallback OK — {len(results)} results[/green]")
            cb.emit("tool_ok", agent_role, f"Fallback OK — {len(results)} results", {
                "result_preview": f"Top: {results[0]['title'][:60]}",
            })
        else:
            console.print("[red]>> Fallback also poor — proceeding with original data[/red]")
            cb.emit("tool_fail", agent_role, "Fallback also insufficient", {
                "error": "Low data volume", "recovery": "Proceeding with original snippets",
            })
    else:
        cb.emit("confidence", agent_role, f"Data OK — {len(results)} results, {total_chars} chars", {
            "score": min(len(results) + 2, 10),
            "max": 10,
            "threshold": 5,
            "reason": f"Deterministic check: {len(results)} results, {total_chars} chars — sufficient",
            "low": False,
        })

    # ── LLM SYNTHESIS ─────────────────────────────────────────────────────────
    cb.emit("step", agent_role, f"{agent_label} — synthesising findings", {
        "step": agent_label, "status": "running",
        "detail": "LLM extracting key insights from data",
    })

    user_prompt = user_prompt_template.format(
        company=company_name, sector=sector,
        competitors=competitor_str, snippets="\n---\n".join(snippets),
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    llm_findings = call_llm(messages)
    preview = llm_findings[:200]
    console.print(f"[dim]  Findings: {preview}...[/dim]")
    cb.emit("findings", agent_role, "LLM findings ready", {"preview": preview})

    # ── PYDANTIC VALIDATE ─────────────────────────────────────────────────────
    result_dict = {
        "agent_role": agent_role, "company": company_name,
        "findings": llm_findings, "sources": sources,
        "raw_snippets": [r["content"][:200] for r in results[:3]],
    }
    cb.emit("tool_call", agent_role, "pydantic_json_validator(schema='ResearchResult')", {
        "tool": "pydantic_json_validator", "args_preview": "schema=ResearchResult",
    })
    validation = pydantic_json_validator(json.dumps(result_dict), "ResearchResult")

    if not validation["valid"]:
        if any("findings" in str(e) for e in validation["errors"]):
            result_dict["findings"] = f"{agent_role} analysis: " + llm_findings
        validation = pydantic_json_validator(json.dumps(result_dict), "ResearchResult")

    cb.emit("validate", agent_role, f"Pydantic valid={validation['valid']}", {
        "valid": validation["valid"], "errors": validation.get("errors", []),
    })
    cb.emit("step", agent_role, f"{agent_label} — complete", {
        "step": agent_label, "status": "done",
        "detail": f"Valid={validation['valid']}",
    })
    console.print(f"[green]>> Pydantic valid={validation['valid']}[/green]")

    return {
        "research_results": [validation["data"] if validation["valid"] else result_dict],
        "error_log": [],
    }
