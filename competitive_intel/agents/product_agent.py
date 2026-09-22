"""
competitive_intel/agents/product_agent.py
------------------------------------------
Parallel Worker — Product & Technology Analysis

The query is dynamically constructed using the company's sector so that
searches target the actual domain (e.g., "trading technology" for a
prop-trading firm instead of generic "product features").
"""

from competitive_intel.agents.worker_base import run_worker
from competitive_intel.llm import call_llm
from competitive_intel.state import WorkerPayload
import json


SYSTEM_PROMPT = (
    "You are a product analyst specialising in competitive intelligence. "
    "From the provided web search snippets, identify:\n"
    "1. Core product/technology pillars and main capabilities\n"
    "2. Unique strengths vs competitors\n"
    "3. Notable gaps or weaknesses\n"
    "Be specific. Use short bullet points. Cite product names when possible."
)

USER_PROMPT_TEMPLATE = (
    "Company: {company} | Sector: {sector} | Competitors: {competitors}\n\n"
    "Web search snippets:\n{snippets}\n\n"
    "Write a concise Product & Technology analysis (2-3 bullet points per section)."
)


def _build_dynamic_query(company: str, sector: str, summary: str) -> str:
    """Ask LLM to generate the best search query for this company+sector+summary."""
    messages = [
        {
            "role": "system",
            "content": (
                "You generate highly deterministic, extremely short web search queries. "
                "Given a company name, its sector, and summary, output a single search query "
                "to find its core products or technology. "
                "Rules: MAXIMUM 3 to 4 words. NO filler words (like 'find', 'about', 'the'). "
                "Output ONLY the query string, nothing else. No quotes."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Company: {company}\nSector: {sector}\nCompany Summary: {summary}\n\n"
                "Query format: <Company Name> <1-2 sector specific keywords>\n"
                "Example for finance: Futures First trading technology\n"
                "Generate the query now:"
            ),
        },
    ]
    query = call_llm(messages).strip().strip('"').strip("'")
    # Ensure company name is in the query
    if company.lower() not in query.lower():
        query = f'"{company}" {query}'
    return query


def product_agent_node(payload: WorkerPayload) -> dict:
    company = payload["company_name"]
    sector = payload["sector"]
    summary = payload.get("company_summary", "")

    query = _build_dynamic_query(company, sector, summary)

    return run_worker(
        agent_role="product_agent",
        company_name=company,
        sector=sector,
        competitors=payload["competitors"],
        search_kwargs={
            "query": query,
            "max_results": 6,
            "search_depth": "advanced",
        },
        system_prompt=SYSTEM_PROMPT,
        user_prompt_template=USER_PROMPT_TEMPLATE,
        simulate_failure=False,
    )
