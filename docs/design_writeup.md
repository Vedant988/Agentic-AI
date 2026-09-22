# CompIntel — Design Write-Up

**System:** Multi-Agent Competitive Intelligence Pipeline  
**Stack:** LangGraph · Groq LLM · Tavily Search API · Streamlit  

---

## Design Decisions

**1. Ground-Truth Baseline Before Any Analysis**  
The most critical design decision was forcing the Orchestrator to extract a verified `company_summary`, `sector`, `HQ`, and `competitors` from its initial web search *before* dispatching any specialist agents. Earlier versions allowed the LLM to guess the company's sector from its name, causing a cascade failure — "Futures First" was hallucinated as an EdTech company, making every downstream query wrong. Anchoring all agents to web-verified ground truth solved this entirely.

**2. Fan-Out / Fan-In Topology via LangGraph Send API**  
The three parallel agents (Product, Sentiment, News) run concurrently using LangGraph's `Send()` API rather than sequentially. This reduces total wall-clock time by ~60% for a typical run. The `OverallState` TypedDict uses `operator.add` reducers on list fields so each agent appends its findings safely without race conditions.

**3. Deterministic Quality Checks over LLM Confidence Scoring**  
An earlier iteration asked an LLM to score each agent's output confidence (0–10) and trigger fallback searches if the score was low. This proved deeply unreliable — the LLM would flag good data as "low confidence" or pass bad data as "high confidence" based on superficial pattern matching. The system now uses deterministic metrics (result count ≥ 2, character volume ≥ 500 chars) which are fast, cheap, and reproducible.

**4. Short, Deterministic Search Queries**  
Rather than having agents formulate long descriptive queries, they are instructed to produce ≤ 4-word, sector-specific queries (e.g., `SatLab GNSS LiDAR surveying`). Longer queries diluted Tavily's relevance ranking; shorter, precise queries significantly improved result quality. The LLM receives the ground-truth `company_summary` as context to ensure the query targets the right domain.

**5. Advanced Tavily Search Depth**  
All Tavily calls use `search_depth="advanced"`, which retrieves deeper page content at the cost of slightly higher latency (~1-2s per call). For competitive intelligence, depth is far more valuable than speed — shallow snippets frequently missed key product or news details.

---

## Limitations

- **API Rate Limits:** The system makes 4-5 Tavily API calls per run (1 orchestrator + 3 agents + possible retries). On Tavily's free tier (1,000/month), heavy usage can exhaust the quota quickly.
- **LLM Query Generation Latency:** Each parallel agent makes one LLM call just to generate a search query before the actual Tavily call. This adds ~0.5–1s latency per agent and costs tokens. A hardcoded template approach would be faster.
- **Private / Obscure Companies:** For companies with minimal public web presence (small startups, stealth-mode firms), the system returns sparse results with low character volume, triggering quality fallbacks. The final report is accurate but thin.
- **No Memory / Caching:** Each run starts fresh. Repeated searches for the same company repeat all API calls. A Redis or simple JSON cache for Tavily results would cut costs and latency significantly.
- **Single-Language:** All prompts and synthesis are in English. Non-English company names or press releases may degrade quality.

---

## What I Would Do Differently With More Time

1. **Add a caching layer** (Redis or SQLite) for Tavily results, keyed by `(query, search_depth)`. This would make re-runs near-instant and eliminate duplicate API spend.

2. **Separate query generation from agent execution.** The current architecture burns LLM tokens just to generate a 4-word query. A smarter approach: use a small, fast lookup model for query generation and reserve the large model only for synthesis.

3. **Add a Competitor Deep-Dive agent.** Currently, competitors are identified but not individually researched. A fourth parallel agent that runs one Tavily search per competitor would dramatically enrich the "competitive landscape" section of the report.

4. **Structured output schema for the final report.** The synthesis agent currently produces free-form Markdown. Switching to a Pydantic-validated JSON schema (with typed sections for product, sentiment, news) would make the output programmatically consumable by CRM systems or downstream pipelines.

5. **Streaming UI with real token-level updates.** The Streamlit UI currently polls a queue every 400ms. A proper SSE (Server-Sent Events) or WebSocket channel would give true streaming output, which is especially impactful for the synthesis step.
