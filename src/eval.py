"""
Evaluation harness: run named test cases and measure output quality
across four dimensions per result.

Dimensions
----------
retrieval_hit   Whether the retrieval system surfaced at least one chunk containing
                all expected keywords. Failure here means the vector search is the
                problem — not the generator.

completeness    Whether all expected keywords appear in the generated response.
                Failure means the generator dropped required information even
                though it was available in context.

grounded        Proxy check: response is substantive and does not begin with an
                explicit refusal ("I don't know", "not provided", etc.).
                True faithfulness (does the response invent facts?) requires
                LLM-as-judge; this is a cheap first-pass filter.

passed          True only if all three dimensions pass.
"""
import json

from .generate import generate
from .retrieve import retrieve

TEST_CASES = [
    {
        "id": "tc_001",
        "query": "What indicators of compromise were identified in the phishing campaign?",
        "expected_keywords": ["phishing", "domain", "sender"],
    },
    {
        "id": "tc_002",
        "query": "What are the containment steps for a malware-infected endpoint?",
        "expected_keywords": ["isolat", "network", "endpoint"],
    },
    {
        "id": "tc_003",
        "query": "What is the SLA for a Severity 1 incident?",
        "expected_keywords": ["severity 1", "sla", "hour"],
    },
    {
        "id": "tc_004",
        "query": "What MFA requirements does the access control policy specify?",
        "expected_keywords": ["mfa", "multi-factor", "authenticat"],
    },
    {
        "id": "tc_005",
        "query": "What forensic evidence should be collected during a malware response?",
        "expected_keywords": ["forensic", "memory", "log"],
    },
]

REFUSAL_PHRASES = [
    "i don't know",
    "i cannot",
    "no information",
    "not provided",
    "context does not",
    "not mentioned",
]


def check_retrieval_hit(chunks: list[dict], keywords: list[str]) -> bool:
    combined = " ".join(c["text"] for c in chunks).lower()
    return all(kw.lower() in combined for kw in keywords)


def check_completeness(response: str, keywords: list[str]) -> tuple[bool, list[str]]:
    missing = [kw for kw in keywords if kw.lower() not in response.lower()]
    return len(missing) == 0, missing


def check_grounded(response: str) -> bool:
    if not response or len(response) < 30:
        return False
    return not any(phrase in response.lower() for phrase in REFUSAL_PHRASES)


def run_eval(top_k: int = 3, report_path: str = "eval_report.json") -> None:
    results = []
    print(f"Running {len(TEST_CASES)} eval cases (top_k={top_k})...\n")

    for tc in TEST_CASES:
        chunks = retrieve(tc["query"], top_k=top_k)
        result = generate(tc["query"], chunks)
        response = result["response"]

        r_hit = check_retrieval_hit(chunks, tc["expected_keywords"])
        complete, missing = check_completeness(response, tc["expected_keywords"])
        grounded = check_grounded(response)
        passed = r_hit and complete and grounded

        record = {
            "id": tc["id"],
            "query": tc["query"],
            "retrieval_hit": r_hit,
            "completeness": complete,
            "grounded": grounded,
            "passed": passed,
            "missing_keywords": missing,
            "sources_used": result["sources_used"],
            "response_preview": response[:200],
        }
        results.append(record)

        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {tc['id']}: {tc['query'][:65]}...")
        print(f"       retrieval_hit={r_hit}  completeness={complete}  grounded={grounded}")
        if missing:
            print(f"       missing: {missing}")
        print(f"       sources: {result['sources_used']}")
        print()

    total = len(results)
    print("=" * 60)
    print("EVAL SUMMARY")
    print("=" * 60)
    for dim in ["retrieval_hit", "completeness", "grounded", "passed"]:
        n = sum(1 for r in results if r[dim])
        bar = "#" * n + "-" * (total - n)
        print(f"  {dim:<20} {n}/{total}  [{bar}]")

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull report: {report_path}")
