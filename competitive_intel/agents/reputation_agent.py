"""
competitive_intel/agents/reputation_agent.py
----------------------------------------------
Parallel Worker — Employee & Workplace Sentiment

Renamed from "Reputation Agent". Targets Glassdoor, Indeed, and employee
review sites instead of generic customer reviews. Query is dynamically
constructed using the company's sector.
"""

from competitive_intel.agents.worker_base import run_worker
from competitive_intel.llm import call_llm
from competitive_intel.state import WorkerPayload


SYSTEM_PROMPT = (
    "You are a workplace culture analyst. From the provided web search snippets, "
    "extract insights about:\n"
    "1. Employee satisfaction and workplace culture\n"
    "2. Common praises (what employees like)\n"
    "3. Common complaints (what employees dislike)\n"
    "Be specific. Use short bullet points. Cite sources when possible."
)

USER_PROMPT_TEMPLATE = (
    "Company: {company} | Sector: {sector} | Competitors: {competitors}\n\n"
    "Web search snippets:\n{snippets}\n\n"
    "Write a concise Employee & Workplace Sentiment analysis (2-3 bullet points per section)."
)


def _build_dynamic_query(company: str, sector: str, summary: str) -> str:
    """Ask LLM to generate the best search query for employee sentiment."""
    messages = [
        {
            "role": "system",
            "content": (
                "You generate highly deterministic, extremely short web search queries. "
                "Given a company name, its sector, and summary, output a single search query "
                "to find employee reviews or workplace culture. "
                "Rules: MAXIMUM 3 to 4 words. NO filler words. "
                "Output ONLY the query string, nothing else. No quotes."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Company: {company}\nSector: {sector}\nCompany Summary: {summary}\n\n"
                "Query format: <Company Name> employee reviews\n"
                "Example: Futures First employee reviews\n"
                "Generate the query now:"
            ),
        },
    ]
    query = call_llm(messages).strip().strip('"').strip("'")
    if company.lower() not in query.lower():
        query = f'"{company}" {query}'
    return query


def reputation_agent_node(payload: WorkerPayload) -> dict:
    company = payload["company_name"]
    sector = payload["sector"]
    summary = payload.get("company_summary", "")

    query = _build_dynamic_query(company, sector, summary)

    return run_worker(
        agent_role="reputation_agent",
        company_name=company,
        sector=sector,
        competitors=payload["competitors"],
        search_kwargs={
            "query": query,
            "include_domains": [
                "glassdoor.com",
                "indeed.com",
                "ambitionbox.com",
                "linkedin.com",
            ],
            "max_results": 7,
            "search_depth": "advanced",
        },
        system_prompt=SYSTEM_PROMPT,
        user_prompt_template=USER_PROMPT_TEMPLATE,
        simulate_failure=False,
    )
