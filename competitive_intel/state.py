"""
competitive_intel/state.py
--------------------------
LangGraph state schemas and Pydantic models for the competitive intelligence system.
"""

import operator
from typing import Annotated, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic schemas — used by the pydantic_json_validator tool
# ---------------------------------------------------------------------------

class ResearchResult(BaseModel):
    """Structured output every parallel agent must produce."""
    agent_role: str = Field(..., description="Which agent produced this (e.g. 'product_agent')")
    company: str = Field(..., description="Target company name")
    findings: str = Field(..., min_length=20, description="Key findings in prose or bullet form")
    sources: list[str] = Field(..., min_items=0, description="URLs or source references")
    raw_snippets: list[str] = Field(default_factory=list, description="Raw text snippets from Tavily")


class OrchestratorPlan(BaseModel):
    """The Orchestrator's upfront plan — emitted before any Tavily call."""
    target_company: str
    hypothesis_sector: str = Field(..., description="Agent's initial guess at the sector")
    search_intent: str = Field(..., description="What the search is trying to confirm/deny")
    expected_competitors: list[str] = Field(default_factory=list)


class OrchestratorOutput(BaseModel):
    """What the Orchestrator writes to state after acting."""
    sector: str
    headquarters: str = Field(..., description="The city and country where the company is headquartered")
    competitors: list[str] = Field(..., min_items=1, max_items=5)
    company_summary: str = Field(..., description="1-2 sentences explaining exactly what this company does.")


# ---------------------------------------------------------------------------
# LangGraph State Schemas
# ---------------------------------------------------------------------------

class OverallState(TypedDict):
    """Master graph state shared across all nodes."""
    company_name: str
    # Set by Orchestrator (Step 1)
    sector: str
    headquarters: str
    competitors: list[str]
    company_summary: str
    # Accumulated by all parallel workers via operator.add reducer
    research_results: Annotated[list[dict], operator.add]
    # Synthesis & retry
    retry_count: int
    missing_sections: list[str]          # sections synthesis found empty
    should_retry: bool
    # Final output
    final_report: str
    # Planning trace — accumulated across all agents
    planning_trace: Annotated[list[str], operator.add]
    # Error log — accumulated across all agents
    error_log: Annotated[list[str], operator.add]


class WorkerPayload(TypedDict):
    """Per-agent payload dispatched via Send()."""
    company_name: str
    company_summary: str
    sector: str
    competitors: list[str]
    agent_role: str   # "product" | "pricing" | "reputation" | "news"
