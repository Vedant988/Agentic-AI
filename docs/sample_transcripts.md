# CompIntel — Sample Run Transcripts

Three representative runs demonstrating the agent's planning, tool calls, and final output.

---

## Run 1: Notion (Productivity SaaS)

### Planning Trace (Orchestrator — Phase 1)
```json
{
  "target_company": "Notion",
  "research_objective": "Competitive intelligence: product landscape, employee sentiment, market news",
  "plan_steps": [
    "Search Notion sector, competitors, and HQ via Tavily",
    "Dispatch Product Agent: search Notion product features and capabilities",
    "Dispatch Sentiment Agent: search Notion employee reviews on Glassdoor/Indeed",
    "Dispatch News Agent: search Notion news and announcements",
    "Synthesize all findings into structured brief"
  ],
  "expected_sector": "Productivity Software / SaaS",
  "potential_risks": ["ambiguous company name", "incomplete pricing data"]
}
```

### Orchestrator Ground Truth Extraction
```
>> Sector:      Productivity Software
>> HQ:          San Francisco, California, USA
>> Competitors: Airtable, Craft, Scribe
>> Summary:     Notion is an all-in-one productivity platform combining notes,
                wikis, databases, and project management in a single workspace,
                targeted at individuals and teams.
```

### Tool Calls (Phase 2 — Parallel)
| Agent          | Query Generated          | Results | Characters |
|----------------|--------------------------|---------|------------|
| Product Agent  | `Notion workspace features`  | 6       | 14,200     |
| Sentiment Agent| `Notion employee reviews`    | 7       | 9,800      |
| News Agent     | `Notion news announcements`  | 7       | 11,500     |

### Final Report Excerpt
> **Market Position:** Notion sits at the intersection of note-taking, knowledge-base, and low-code database. Its unified-workspace model differentiates it from siloed competitors.
> **Strategic Signal:** Google's shutdown of *Tables* creates a migration opportunity toward Notion's relational-database blocks.
> **Risk:** Public sentiment is mixed (Trustpilot ≈ 2.2/5). Brand perception work is needed.

---

## Run 2: Futures First (Proprietary Trading)

### Planning Trace (Orchestrator — Phase 1)
```json
{
  "target_company": "Futures First",
  "research_objective": "Competitive intelligence: trading technology, firm culture, market signals",
  "plan_steps": [
    "Search Futures First to establish ground truth (prevent sector ambiguity)",
    "Dispatch Product Agent: trading platform and technology capabilities",
    "Dispatch Sentiment Agent: trader reviews and work culture",
    "Dispatch News Agent: recent firm news and hiring signals",
    "Synthesize findings"
  ],
  "expected_sector": "Proprietary Quantitative Trading",
  "potential_risks": ["name ambiguity with EdTech companies"]
}
```

### Orchestrator Ground Truth Extraction
```
>> Sector:      Proprietary Quantitative Trading
>> HQ:          Gurgaon, India
>> Competitors: Optiver, Flow Traders, IMC Trading
>> Summary:     Futures First is a large proprietary quantitative trading firm
                specialising in futures and options markets globally, operating
                from India and internationally.
```

### Tool Calls (Phase 2 — Parallel)
| Agent          | Query Generated              | Results | Characters |
|----------------|------------------------------|---------|------------|
| Product Agent  | `Futures First trading technology` | 5  | 8,700      |
| Sentiment Agent| `Futures First employee reviews`   | 7  | 12,400     |
| News Agent     | `Futures First news`               | 6  | 7,200      |

**Note:** With the old LLM-based sanity check, this run used to fail. The Orchestrator misidentified the company as EdTech, causing all agents to search with wrong context. With the ground-truth baseline approach, the firm is correctly identified from web data on the very first search.

### Final Report Excerpt
> **Product & Technology:** Futures First operates a proprietary algorithmic trading infrastructure for futures and options. Focus is on in-house quant research, low-latency execution, and risk management systems.
> **Employee Sentiment:** Highly competitive environment with steep learning curve. Positive reviews cite strong compensation and mentorship from senior traders. Negative reviews cite high pressure and long hours.
> **News & Momentum:** Limited public news — consistent with a secretive prop-trading firm that does not make press announcements.

---

## Run 3: SatLab (Geospatial / Surveying Equipment)

### Planning Trace (Orchestrator — Phase 1)
```json
{
  "target_company": "SatLab",
  "research_objective": "Competitive intelligence: GNSS/LiDAR product range, workplace culture, recent announcements",
  "plan_steps": [
    "Ground truth web search for SatLab Geosolutions",
    "Dispatch Product Agent: GNSS and LiDAR product capabilities",
    "Dispatch Sentiment Agent: SatLab workplace sentiment",
    "Dispatch News Agent: SatLab recent product launches and events",
    "Synthesize all findings"
  ],
  "expected_sector": "Geospatial / Surveying Equipment",
  "potential_risks": ["small company — limited public data"]
}
```

### Orchestrator Ground Truth Extraction
```
>> Sector:      Geospatial / Surveying & Mapping Equipment
>> HQ:          Gothenburg, Sweden
>> Competitors: Trimble, Leica Geosystems, NavVis
>> Summary:     SatLab Geosolutions is a Swedish manufacturer of professional
                GNSS, RTK, LiDAR, and hydrographic survey equipment used in
                land surveying, 3D mapping, and UAV applications.
```

### Tool Calls (Phase 2 — Parallel)
| Agent          | Query Generated              | Results | Characters |
|----------------|------------------------------|---------|------------|
| Product Agent  | `SatLab GNSS LiDAR surveying` | 6      | 10,679     |
| Sentiment Agent| `SatLab employee reviews`     | 4      | 5,200      |
| News Agent     | `SatLab news`                 | 7      | 10,679     |

### Final Report Excerpt
> **Product Highlights:** SatLab's Cygnus 3 SLAM PRO + Sat-LiDAR enables high-precision 3D mapping in motion. The UAV/RTK receiver integrates 4G modem and Bluetooth for field-ready deployments.
> **News:** SatLab showcased at INTERGEO 2026 in Munich. Company offering free 3-day exhibition tickets — indicating active sales push.
> **Sentiment:** Limited public employee data — company appears small and privately held with minimal Glassdoor presence.
