"""
Stress test script — run this on your machine (Mac, with tunnel active)
to test multiple real-world farmer scenarios across schemes and languages.
Prints a final summary showing which LLM backend answered each query.
"""

from core import agent_engine

test_cases = [
    {"label": "1. Irrigation subsidy query (Hindi)",
     "query": "mujhe khet mein paani ki samasya hai, koi sarkari madad milegi kya", "language": "hi"},
    {"label": "2. Crop insurance after flood damage (Hindi)",
     "query": "baadh mein meri fasal kharab ho gayi, mujhe paisa milega kya", "language": "hi"},
    {"label": "3. Wants a tractor, can't afford it (English)",
     "query": "I want to buy a tractor but I cannot afford the full price, is there any subsidy", "language": "en"},
    {"label": "4. LPG connection for wife (Hindi)",
     "query": "meri patni ke liye gas connection chahiye, hum garib hain", "language": "hi"},
    {"label": "5. Completely unrelated query - should trigger fallback",
     "query": "what is the best biryani recipe", "language": "en"},
    {"label": "6. Job/employment guarantee scheme (Hindi)",
     "query": "gaon mein kaam nahi hai, sarkar kaam deti hai kya", "language": "hi"},
    {"label": "7. Vague/ambiguous query - tests retrieval threshold",
     "query": "kisan ke liye kya hai", "language": "hi"},
    {"label": "8. House construction help (Hindi)",
     "query": "mera ghar kaccha hai, pakka ghar banane ke liye paisa chahiye", "language": "hi"},
]

print("=" * 70)
print("JAN SAHAYAK — STRESS TEST")
print("=" * 70)

summary = []

for case in test_cases:
    print(f"\n{case['label']}")
    print(f"Query: {case['query']}")
    print("-" * 70)
    result = agent_engine.handle_query(case["query"], language=case["language"])
    print(f"Grounded: {result['grounded']}")
    print(f"Backend used: {result['backend_used']}")
    print(f"Schemes: {result['schemes_referenced']}")
    print(f"Answer:\n{result['answer']}")
    print("=" * 70)
    summary.append({
        "label": case["label"],
        "grounded": result["grounded"],
        "backend": result["backend_used"] or "fallback (no LLM called)",
        "schemes": result["schemes_referenced"],
    })

print("\n" + "=" * 70)
print("SUMMARY REPORT — Which backend answered each question")
print("=" * 70)
for s in summary:
    status = "GROUNDED" if s["grounded"] else "FALLBACK"
    print(f"[{status:8}] {s['label']}")
    print(f"           Backend: {s['backend']}")
    if s["schemes"]:
        print(f"           Schemes: {', '.join(s['schemes'])}")
    print()

grounded_count = sum(1 for s in summary if s["grounded"])
print(f"Total: {grounded_count}/{len(summary)} queries answered with grounded evidence")
print("\nTest run complete.")
