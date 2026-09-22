"""
Scratch script: test each worker agent individually against "Futures First"
to see which ones return useful data vs false positives.
"""
import sys, io, json, os
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from competitive_intel.tools import tavily_search

COMPANY = "Futures First"

queries = {
    "Product Agent": f'"{COMPANY}" product features value proposition',
    "Pricing Agent": f'"{COMPANY}" pricing tiers plans cost',
    "Reputation Agent": f'{COMPANY} reviews complaints user experience',
    "News Agent": f'"{COMPANY}" news announcement launch',
}

print("=" * 80)
print(f"TESTING TAVILY QUERIES FOR: {COMPANY}")
print("=" * 80)

for agent, query in queries.items():
    print(f"\n{'─' * 60}")
    print(f"  AGENT: {agent}")
    print(f"  QUERY: {query}")
    print(f"{'─' * 60}")

    result = tavily_search(query=query, max_results=5, search_depth="basic")

    if not result["success"]:
        print(f"  ✗ FAILED: {result['error']}")
        continue

    results = result["results"]
    print(f"  → {len(results)} results\n")

    for i, r in enumerate(results[:5], 1):
        title = r["title"][:70]
        url = r["url"][:80]
        snippet = r["content"][:150].replace("\n", " ")
        print(f"  [{i}] {title}")
        print(f"      URL: {url}")
        print(f"      Snippet: {snippet}...")
        print()

print("\n" + "=" * 80)
print("DONE — Review which agents returned relevant data above.")
print("=" * 80)
