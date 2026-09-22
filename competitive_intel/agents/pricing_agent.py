"""
competitive_intel/agents/pricing_agent.py
------------------------------------------
Parallel Worker — Pricing & Positioning Analysis

Goal: Extract exact pricing tiers, packaging, and target customer profiles.
"""

from competitive_intel.agents.worker_base import run_worker
from competitive_intel.state import WorkerPayload


SYSTEM_PROMPT = (
    "You are a pricing analyst specialising in SaaS and tech competitive intelligence. "
    "From web search snippets, identify:\n"
    "1. Pricing tiers and plan names (Free, Pro, Enterprise, etc.)\n"
    "2. Price points (monthly/annual) if available\n"
    "3. Target customer segments (SMB, Mid-Market, Enterprise)\n"
    "4. Packaging differences vs competitors\n"
    "Be precise. If exact prices are unavailable, note the pricing model (usage-based, seat-based, etc.)."
)

USER_PROMPT_TEMPLATE = (
    "Company: {company} | Sector: {sector} | Competitors: {competitors}\n\n"
    "Web search snippets:\n{snippets}\n\n"
    "Write a Pricing & Positioning analysis covering tiers, prices, and customer targets."
)


def pricing_agent_node(payload: WorkerPayload) -> dict:
    competitors = payload["competitors"]
    comp_str = " OR ".join(f'"{c}"' for c in competitors[:2]) if competitors else ""
    query = f'"{payload["company_name"]}" {comp_str} pricing tiers plans cost'.strip()

    return run_worker(
        agent_role="pricing_agent",
        company_name=payload["company_name"],
        sector=payload["sector"],
        competitors=competitors,
        search_kwargs={
            "query": query,
            "max_results": 6,
            "search_depth": "basic",
        },
        system_prompt=SYSTEM_PROMPT,
        user_prompt_template=USER_PROMPT_TEMPLATE,
        simulate_failure=False,
    )
