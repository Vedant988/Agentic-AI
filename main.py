"""
main.py
--------
CLI entry point for the Competitive Intelligence Multi-Agent System.

Usage:
    python main.py "Notion"
    python main.py "Stripe"
    python main.py          (prompts interactively)

Output:
    - Streaming console trace (planning -> execution -> synthesis)
    - Final markdown report saved to: report_<company>.md
"""

import sys
import io

# Force UTF-8 on Windows console so Rich emojis/unicode don't crash cp1252
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import json
import time
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from dotenv import load_dotenv

load_dotenv()

console = Console()


def print_banner():
    console.print(Panel(
        "[bold cyan]Competitive Intelligence Multi-Agent System[/bold cyan]\n"
        "[dim]Powered by LangGraph + Groq gpt-oss-120b + Tavily[/dim]\n\n"
        "[white]Agents:[/white]\n"
        "  [green]1.[/green] Orchestrator        (Sequential)\n"
        "  [green]2.[/green] Product Agent       | Parallel Fan-Out\n"
        "  [green]3.[/green] Pricing Agent       | via Send() API\n"
        "  [green]4.[/green] Reputation Agent    | (all concurrent)\n"
        "  [green]5.[/green] News Agent [FAIL]   | demos failure+recovery\n"
        "  [green]6.[/green] Synthesis Agent     (Sequential)\n",
        title="[bold white]>> CompIntel v1.0[/bold white]",
        border_style="cyan",
        padding=(1, 4),
    ))


def print_execution_plan(company: str):
    """Print a high-level execution plan before the graph runs."""
    console.rule("[bold white]📋 SYSTEM-LEVEL EXECUTION PLAN")

    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Step", style="cyan", width=6)
    table.add_column("Agent", style="white", width=25)
    table.add_column("Type", style="yellow", width=20)
    table.add_column("Tool Strategy", style="green")

    table.add_row("1", "Orchestrator", "Sequential",
                  f'tavily_search("{company} market sector competitors")')
    table.add_row("2a", "Product Agent", "Parallel Fan-Out",
                  'tavily_search → corporate + tech blog queries')
    table.add_row("2b", "Pricing Agent", "Parallel Fan-Out",
                  'tavily_search → pricing tiers plans cost')
    table.add_row("2c", "Reputation Agent", "Parallel Fan-Out",
                  'tavily_search(include_domains=[reddit, g2, trustradius])')
    table.add_row("2d", "News Agent ⚡", "Parallel Fan-Out",
                  'tavily_search(topic=news, time_range=week) → FAILS → recovery')
    table.add_row("3", "Synthesis Guard", "Sequential",
                  "No Tavily — pure LLM reasoning + pydantic_json_validator")
    table.add_row("*", "Self-Correction", "Conditional Loop",
                  "Retry if sections missing (max 2 retries)")

    console.print(table)
    console.print()
    console.print("[dim]Tools used:[/dim]")
    console.print("  [cyan]①[/cyan] [bold]tavily_search[/bold]        — real-time web search with full parameter control")
    console.print("  [cyan]②[/cyan] [bold]pydantic_json_validator[/bold] — validates every agent output against ResearchResult schema")
    console.print()


def save_report(company: str, report: str, state: dict) -> Path:
    """Save structured JSON + markdown report to disk."""
    safe_name = company.lower().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save markdown report
    md_path = Path(f"report_{safe_name}.md")
    md_path.write_text(report, encoding="utf-8")

    # Save full JSON state dump
    json_path = Path(f"report_{safe_name}_state.json")
    state_dump = {
        "company_name": state.get("company_name"),
        "sector": state.get("sector"),
        "competitors": state.get("competitors"),
        "retry_count": state.get("retry_count", 0),
        "planning_trace": state.get("planning_trace", []),
        "error_log": state.get("error_log", []),
        "research_results_count": len(state.get("research_results", [])),
        "timestamp": timestamp,
    }
    json_path.write_text(json.dumps(state_dump, indent=2), encoding="utf-8")

    return md_path


def main():
    print_banner()

    # ── Get company name ──────────────────────────────────────────────────────
    if len(sys.argv) > 1:
        company = " ".join(sys.argv[1:]).strip()
    else:
        company = console.input("[bold cyan]Enter company name:[/bold cyan] ").strip()

    if not company:
        console.print("[bold red]Error:[/bold red] Company name cannot be empty.")
        sys.exit(1)

    console.print(f"\n[bold]Target company:[/bold] [green]{company}[/green]\n")

    # ── Print system-level execution plan ─────────────────────────────────────
    print_execution_plan(company)

    # ── Confirm before running ────────────────────────────────────────────────
    console.print("[dim]Starting graph execution now...[/dim]\n")
    time.sleep(0.5)

    # ── Import and run graph ──────────────────────────────────────────────────
    from competitive_intel.graph import graph

    initial_state = {
        "company_name": company,
        "sector": "",
        "competitors": [],
        "research_results": [],
        "retry_count": 0,
        "missing_sections": [],
        "should_retry": False,
        "final_report": "",
        "planning_trace": [],
        "error_log": [],
    }

    start_time = time.time()

    try:
        final_state = graph.invoke(
            initial_state,
            config={"max_concurrency": 4},   # run all 4 parallel workers concurrently
        )
    except Exception as exc:
        console.print(f"\n[bold red]Graph execution error:[/bold red] {exc}")
        raise

    elapsed = time.time() - start_time

    # ── Display final state summary ───────────────────────────────────────────
    console.rule("[bold green]✅ PIPELINE COMPLETE")

    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column("Key", style="cyan")
    summary_table.add_column("Value", style="white")
    summary_table.add_row("Company",     final_state.get("company_name", company))
    summary_table.add_row("Sector",      final_state.get("sector", "N/A"))
    summary_table.add_row("Competitors", ", ".join(final_state.get("competitors", [])))
    summary_table.add_row("Retries",     str(final_state.get("retry_count", 0)))
    summary_table.add_row("Errors",      str(len(final_state.get("error_log", []))))
    summary_table.add_row("Elapsed",     f"{elapsed:.1f}s")
    console.print(summary_table)

    # ── Print planning trace ───────────────────────────────────────────────────
    traces = final_state.get("planning_trace", [])
    if traces:
        console.rule("[bold cyan]📋 FULL PLANNING TRACE")
        for i, trace in enumerate(traces, 1):
            console.print(f"[dim cyan][{i}] {trace}[/dim cyan]\n")

    # ── Print error log ───────────────────────────────────────────────────────
    errors = final_state.get("error_log", [])
    if errors:
        console.rule("[bold yellow]⚠ ERROR LOG (recovered)")
        for err in errors:
            console.print(f"  [yellow]•[/yellow] {err}")

    # ── Save and display report path ──────────────────────────────────────────
    report = final_state.get("final_report", "")
    if report:
        md_path = save_report(company, report, final_state)
        console.print(f"\n[bold green]📄 Report saved:[/bold green] {md_path.resolve()}")
        console.print(f"[bold green]📊 State dump:[/bold green]  {md_path.with_suffix('').name}_state.json\n")
    else:
        console.print("[yellow]⚠ No report generated.[/yellow]")


if __name__ == "__main__":
    main()
