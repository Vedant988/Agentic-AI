"""
competitive_intel/agents/news_agent.py
---------------------------------------
Parallel Worker — Recent News & Momentum Analysis

Goal: Track recent launches, funding, partnerships, acquisitions, leadership
changes for the company and its top competitors.

⚠️  DELIBERATE FAILURE DEMO:
    This agent deliberately triggers a TimeoutError on its FIRST call
    (simulate_failure=True) to demonstrate graceful error recovery.
    The worker_base catches it, logs it, and retries with a simplified query.
"""

from competitive_intel.agents.worker_base import run_worker
from competitive_intel.llm import call_llm
from competitive_intel.state import WorkerPayload


SYSTEM_PROMPT = (
    "You are a market intelligence analyst tracking recent business news. "
    "From news snippets, identify:\n"
    "1. Product launches or major updates\n"
    "2. Funding rounds, acquisitions, or partnerships\n"
    "3. Leadership changes (CEO, CTO, etc.)\n"
    "4. Strategic signals indicating direction of the company\n"
    "Prioritise recency and business impact. Note approximate dates if visible."
)

USER_PROMPT_TEMPLATE = (
    "Company: {company} | Sector: {sector} | Competitors: {competitors}\n\n"
    "Recent news snippets:\n{snippets}\n\n"
    "Write a Recent News & Momentum brief with the most strategically significant events."
)


def _build_dynamic_query(company: str, sector: str, summary: str, competitors: list[str]) -> str:
    """Ask LLM to generate the best search query for recent news."""
    comp_str = f"\nCompetitors: {', '.join(competitors[:2])}" if competitors else ""
    messages = [
        {
            "role": "system",
            "content": (
                "You generate highly deterministic, extremely short web search queries. "
                "Given a company name, its sector, and summary, output a single search query "
                "to find recent business news or strategic moves. "
                "Rules: MAXIMUM 3 to 4 words. NO filler words. "
                "Output ONLY the query string, nothing else. No quotes."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Company: {company}\nSector: {sector}\nCompany Summary: {summary}{comp_str}\n\n"
                "Query format: <Company Name> news\n"
                "Example: Futures First news announcements\n"
                "Generate the query now:"
            ),
        },
    ]
    query = call_llm(messages).strip().strip('"').strip("'")
    if company.lower() not in query.lower():
        query = f'"{company}" {query}'
    return query


def news_agent_node(payload: WorkerPayload) -> dict:
    company = payload["company_name"]
    sector = payload["sector"]
    summary = payload.get("company_summary", "")
    competitors = payload["competitors"]
    
    query = _build_dynamic_query(company, sector, summary, competitors)

    return run_worker(
        agent_role="news_agent",
        company_name=payload["company_name"],
        sector=payload["sector"],
        competitors=competitors,
        search_kwargs={
            "query": query,
            "topic": "news",
            "max_results": 7,
            "search_depth": "advanced",
        },
        system_prompt=SYSTEM_PROMPT,
        user_prompt_template=USER_PROMPT_TEMPLATE,
        # ── DELIBERATE FAILURE: disabled by user request ──────────────
        simulate_failure=False,
    )
