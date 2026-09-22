"""
competitive_intel/graph.py
---------------------------
LangGraph graph assembly.

Topology:
  START
    └─► orchestrator_node            (Sequential — Step 1)
          └─► fan_out_router          (Conditional edge using Send API)
                ├─► product_worker    ┐
                ├─► reputation_worker │  Parallel fan-out — Step 2
                └─► news_worker       ┘  (all run concurrently)
                      ↓ (all merge via operator.add reducer)
                    fan_in_node        (triggers synthesis)
                      └─► synthesis_node  (Sequential — Step 3)
                            ├─► [retry?] → orchestrator_node  (self-correction loop)
                            └─► END

Pricing Agent has been removed to reduce false-positive noise.
"""

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from competitive_intel.state import OverallState, WorkerPayload
from competitive_intel.agents.orchestrator import orchestrator_node
from competitive_intel.agents.product_agent import product_agent_node
from competitive_intel.agents.reputation_agent import reputation_agent_node
from competitive_intel.agents.news_agent import news_agent_node
from competitive_intel.agents.synthesis_agent import synthesis_node


# ─────────────────────────────────────────────────────────────────────────────
# Wrapper nodes for parallel workers
# ─────────────────────────────────────────────────────────────────────────────

def product_worker(payload: WorkerPayload) -> dict:
    return product_agent_node(payload)


def reputation_worker(payload: WorkerPayload) -> dict:
    return reputation_agent_node(payload)


def news_worker(payload: WorkerPayload) -> dict:
    return news_agent_node(payload)


# ─────────────────────────────────────────────────────────────────────────────
# Fan-out router — dispatches parallel Send() calls
# ─────────────────────────────────────────────────────────────────────────────

def fan_out_router(state: OverallState) -> list[Send]:
    """
    After orchestrator sets sector + competitors, dispatch 3 parallel
    agents simultaneously using the Send API.
    """
    payload: WorkerPayload = {
        "company_name": state["company_name"],
        "company_summary": state.get("company_summary", ""),
        "sector": state.get("sector", "Technology"),
        "competitors": state.get("competitors", []),
        "agent_role": "",
    }

    return [
        Send("product_worker",    {**payload, "agent_role": "product_agent"}),
        Send("reputation_worker", {**payload, "agent_role": "reputation_agent"}),
        Send("news_worker",       {**payload, "agent_role": "news_agent"}),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Fan-in passthrough
# ─────────────────────────────────────────────────────────────────────────────

def fan_in_node(state: OverallState) -> dict:
    """Receives merged research_results from all parallel workers. No-op."""
    from rich.console import Console
    Console().rule("[bold blue]Fan-In: All parallel agents complete. Proceeding to Synthesis.")
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Retry condition
# ─────────────────────────────────────────────────────────────────────────────

def should_retry(state: OverallState) -> str:
    if state.get("should_retry", False) and state.get("retry_count", 0) <= 2:
        return "retry"
    return "done"


# ─────────────────────────────────────────────────────────────────────────────
# Graph construction
# ─────────────────────────────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(OverallState)

    # Step 1 — Sequential
    builder.add_node("orchestrator_node", orchestrator_node)

    # Step 2 — Parallel workers (3 agents, no pricing)
    builder.add_node("product_worker",    product_worker)
    builder.add_node("reputation_worker", reputation_worker)
    builder.add_node("news_worker",       news_worker)

    # Fan-in and Step 3
    builder.add_node("fan_in_node",   fan_in_node)
    builder.add_node("synthesis_node", synthesis_node)

    # Edges
    builder.add_edge(START, "orchestrator_node")

    # Conditional fan-out after orchestrator
    builder.add_conditional_edges(
        "orchestrator_node",
        fan_out_router,
        ["product_worker", "reputation_worker", "news_worker"],
    )

    # All parallel workers converge into fan_in_node
    builder.add_edge("product_worker",    "fan_in_node")
    builder.add_edge("reputation_worker", "fan_in_node")
    builder.add_edge("news_worker",       "fan_in_node")

    # Fan-in → synthesis
    builder.add_edge("fan_in_node", "synthesis_node")

    # Self-correction loop
    builder.add_conditional_edges(
        "synthesis_node",
        should_retry,
        {
            "retry": "orchestrator_node",
            "done": END,
        },
    )

    return builder.compile()


# Singleton compiled graph
graph = build_graph()
