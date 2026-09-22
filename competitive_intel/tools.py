"""
competitive_intel/tools.py
--------------------------
Tool 1: tavily_search    — parameterized Tavily web search
Tool 2: pydantic_json_validator — validates JSON against a named Pydantic schema

Both tools follow LangChain @tool convention so they can be bound to agents
and also called directly from node functions.
"""

import json
import os
import time
from typing import Optional

from dotenv import load_dotenv
from pydantic import ValidationError
from tavily import TavilyClient

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Tavily client (lazy singleton)
# ─────────────────────────────────────────────────────────────────────────────
_tavily_client: Optional[TavilyClient] = None


def _get_tavily() -> TavilyClient:
    global _tavily_client
    if _tavily_client is None:
        api_key = os.getenv("TAVILY_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError("TAVILY_API_KEY is not set in .env")
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


# ─────────────────────────────────────────────────────────────────────────────
# Tool 1 — tavily_search
# ─────────────────────────────────────────────────────────────────────────────

def tavily_search(
    query: str,
    topic: str = "general",
    time_range: Optional[str] = None,
    include_domains: Optional[list] = None,
    max_results: int = 5,
    search_depth: str = "advanced",
    simulate_failure: bool = False,
) -> dict:
    """
    Search the web using Tavily API with full parameterisation.

    Args:
        query:           The search query string.
        topic:           "general" or "news".
        time_range:      "day" | "week" | "month" | "year" (None = no filter).
        include_domains: Restrict results to these domains (e.g. ["reddit.com"]).
        max_results:     Number of results to return (1-10).
        search_depth:    "basic" | "advanced".
        simulate_failure: If True, raises a deliberate TimeoutError for demo.

    Returns:
        dict with keys:
            success (bool), results (list[dict]), error (str | None)
    """
    # ── Deliberate failure injection for demo ────────────────────────────────
    if simulate_failure:
        raise TimeoutError(
            "[DELIBERATE FAILURE] Tavily search timed out after 10s — "
            "simulating network failure for error-recovery demo."
        )

    try:
        client = _get_tavily()

        kwargs = {
            "query": query,
            "topic": topic,
            "max_results": max_results,
            "search_depth": search_depth,
        }
        if time_range:
            kwargs["time_range"] = time_range
        if include_domains:
            kwargs["include_domains"] = include_domains

        response = client.search(**kwargs)

        results = []
        for r in response.get("results", []):
            results.append({
                "title":   r.get("title", ""),
                "url":     r.get("url", ""),
                "content": r.get("content", ""),
                "score":   r.get("score", 0.0),
            })

        return {"success": True, "results": results, "error": None}

    except TimeoutError:
        raise  # re-raise deliberate failures
    except Exception as exc:
        return {
            "success": False,
            "results": [],
            "error": f"{type(exc).__name__}: {exc}",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Tool 2 — pydantic_json_validator
# ─────────────────────────────────────────────────────────────────────────────

# Registry of available schemas — import here to avoid circular imports
_SCHEMA_REGISTRY: dict = {}


def _load_schemas():
    """Lazy-load schemas to avoid import loops."""
    global _SCHEMA_REGISTRY
    if not _SCHEMA_REGISTRY:
        from competitive_intel.state import ResearchResult, OrchestratorOutput, OrchestratorPlan
        _SCHEMA_REGISTRY = {
            "ResearchResult": ResearchResult,
            "OrchestratorOutput": OrchestratorOutput,
            "OrchestratorPlan": OrchestratorPlan,
        }
    return _SCHEMA_REGISTRY


def pydantic_json_validator(json_str: str, schema_name: str) -> dict:
    """
    Validate a JSON string against a named Pydantic schema.

    Args:
        json_str:    Raw JSON string to validate.
        schema_name: One of "ResearchResult" | "OrchestratorOutput" | "OrchestratorPlan".

    Returns:
        dict with keys:
            valid (bool), errors (list[str]), data (dict | None)
    """
    schemas = _load_schemas()

    if schema_name not in schemas:
        return {
            "valid": False,
            "errors": [f"Unknown schema '{schema_name}'. Available: {list(schemas.keys())}"],
            "data": None,
        }

    # ── Step 1: parse JSON ───────────────────────────────────────────────────
    try:
        raw_data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        return {
            "valid": False,
            "errors": [f"JSON parse error: {exc}"],
            "data": None,
        }

    # ── Step 2: validate against Pydantic model ──────────────────────────────
    model_class = schemas[schema_name]
    try:
        validated = model_class.model_validate(raw_data)
        return {
            "valid": True,
            "errors": [],
            "data": validated.model_dump(),
        }
    except ValidationError as exc:
        errors = [f"{e['loc']}: {e['msg']}" for e in exc.errors()]
        return {
            "valid": False,
            "errors": errors,
            "data": None,
        }
