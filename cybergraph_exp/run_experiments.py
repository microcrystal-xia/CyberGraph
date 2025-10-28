"""Main experiment runner: Text-to-Cypher evaluation and metrics collection."""
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .config import Config
from .graph_setup import get_driver, reset_and_validate
from .text_to_cypher import translate, validate_cypher_syntax
from .impact_analysis import execute_cypher, analyze_cve_impact, simulate_remediation

BENCHMARK_FILE = Path(__file__).parent / "test_queries.json"


def load_benchmark() -> list:
    with open(BENCHMARK_FILE) as f:
        data = json.load(f)
    return data["queries"]


def evaluate_single_query(driver, query: dict) -> dict:
    """Evaluate one NL→Cypher→Execute→Verify pipeline."""
    nl = query["nl_query"]

    # Step 1: Translate NL → Cypher
    try:
        cypher, translate_latency = translate(nl)
    except Exception as e:
        return {
            "query_id": query["id"],
            "category": query["category"],
            "nl_query": nl,
            "generated_cypher": "",
            "syntax_valid": False,
            "exec_success": False,
            "result_correct": False,
            "translate_latency_ms": 0,
            "exec_latency_ms": 0,
            "total_latency_ms": 0,
            "error": f"Translation error: {e}",
        }

    # Step 2: Validate syntax
    syntax_valid = validate_cypher_syntax(cypher)

    # Step 3: Execute against Neo4j
    rows, exec_success, error, exec_latency = execute_cypher(driver, cypher)

    # Step 4: Verify result correctness
    result_correct = False
    if exec_success:
        # Check count if expected
        count_ok = True
        if "expected_result_count" in query:
            count_ok = len(rows) == query["expected_result_count"]

        # Check expected values appear in results
        values_ok = True
        if query.get("expected_values"):
            result_str = json.dumps(rows)
            values_ok = all(v in result_str for v in query["expected_values"])

        result_correct = count_ok and values_ok

    total_latency = translate_latency + exec_latency

    return {
        "query_id": query["id"],
        "category": query["category"],
        "nl_query": nl,
        "generated_cypher": cypher,
        "expected_cypher": query.get("expected_cypher", ""),
        "syntax_valid": syntax_valid,
        "exec_success": exec_success,
        "result_correct": result_correct,
        "result_count": len(rows) if exec_success else 0,
        "expected_result_count": query.get("expected_result_count"),
        "translate_latency_ms": round(translate_latency, 1),
        "exec_latency_ms": round(exec_latency, 1),
        "total_latency_ms": round(total_latency, 1),
        "error": error,
    }


def aggregate_metrics(results: list) -> dict:
    """Compute per-category and overall metrics."""
    by_cat = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)

    def _compute(items):
        n = len(items)
        if n == 0:
            return {}
        return {
            "count": n,
            "syntax_valid_pct": round(100 * sum(r["syntax_valid"] for r in items) / n, 1),
            "exec_success_pct": round(100 * sum(r["exec_success"] for r in items) / n, 1),
            "result_correct_pct": round(100 * sum(r["result_correct"] for r in items) / n, 1),
            "avg_translate_latency_ms": round(
                sum(r["translate_latency_ms"] for r in items) / n, 1
            ),
            "avg_exec_latency_ms": round(
                sum(r["exec_latency_ms"] for r in items) / n, 1
            ),
            "avg_total_latency_ms": round(
                sum(r["total_latency_ms"] for r in items) / n, 1
            ),
        }

    per_category = {cat: _compute(items) for cat, items in sorted(by_cat.items())}
    overall = _compute(results)

    return {"overall": overall, "per_category": per_category}


def run_impact_analysis_tests(driver) -> dict:
    """Run dedicated impact analysis tests and collect metrics."""
    results = {}

    # Test Log4Shell impact
    start = time.perf_counter()
    log4shell = analyze_cve_impact(driver, "CVE-2021-44228")
    results["log4shell"] = {
        **log4shell,
        "expected_services": ["payment-service", "notification-service"],
        "expected_risk": "CRITICAL",
        "risk_correct": log4shell["risk_level"] == "CRITICAL",
    }

    # Test Spring4Shell impact
    spring4shell = analyze_cve_impact(driver, "CVE-2022-22965")
    results["spring4shell"] = {
        **spring4shell,
        "expected_risk": "HIGH",
        "risk_correct": spring4shell["risk_level"] in ("CRITICAL", "HIGH"),
    }

    # Test remediation
    remediation = simulate_remediation(driver, "payment-service", "test-operator")
    results["remediation"] = remediation

    return results


def run_experiments(query_ids: list = None):
    """Run full experiment suite. Optionally filter by query IDs."""
    print("=" * 60)
    print("CyberGraph Experiment Runner")
    print("=" * 60)

    # Validate config
    Config.validate()
    print(f"LLM Provider: {Config.LLM_PROVIDER} ({Config.LLM_MODEL})")

    # Setup
    print("\n[1/4] Connecting to Neo4j and initializing graph...")
    driver = get_driver()
    validation = reset_and_validate(driver)
    print(f"  Graph: {validation['nodes']} nodes, {validation['edges']} edges ✓")

    # Load benchmark
    print("\n[2/4] Loading benchmark queries...")
    queries = load_benchmark()
    if query_ids:
        queries = [q for q in queries if q["id"] in query_ids]
    print(f"  {len(queries)} queries to evaluate")

    # Run Text-to-Cypher evaluation
    print("\n[3/4] Running Text-to-Cypher evaluation...")
    results = []
    for i, query in enumerate(queries):
        print(f"  [{i+1}/{len(queries)}] {query['nl_query'][:60]}...", end=" ", flush=True)
        # Reset graph before each query to ensure clean state
        reset_and_validate(driver)
        result = evaluate_single_query(driver, query)
        status = "✓" if result["result_correct"] else ("⚠" if result["exec_success"] else "✗")
        print(f"{status} ({result['total_latency_ms']:.0f}ms)")
        results.append(result)

    # Run impact analysis tests
    print("\n[4/4] Running impact analysis tests...")
    reset_and_validate(driver)
    impact_results = run_impact_analysis_tests(driver)
    print(f"  Log4Shell risk: {impact_results['log4shell']['risk_level']} "
          f"({'✓' if impact_results['log4shell']['risk_correct'] else '✗'})")
    print(f"  Remediation: {'✓' if impact_results['remediation']['success'] else '✗'}")

    # Aggregate
    metrics = aggregate_metrics(results)

    # Save results
    Config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Config.RESULTS_DIR / f"experiment_{timestamp}.json"

    output = {
        "timestamp": timestamp,
        "config": {
            "llm_provider": Config.LLM_PROVIDER,
            "llm_model": Config.LLM_MODEL,
            "neo4j_uri": Config.NEO4J_URI,
        },
        "metrics": metrics,
        "impact_analysis": {
            k: {kk: vv for kk, vv in v.items() if kk != "chains"}
            for k, v in impact_results.items()
        },
        "results": results,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    o = metrics["overall"]
    print(f"  Total queries:     {o['count']}")
    print(f"  Syntax valid:      {o['syntax_valid_pct']}%")
    print(f"  Execution success: {o['exec_success_pct']}%")
    print(f"  Result correct:    {o['result_correct_pct']}%")
    print(f"  Avg latency:       {o['avg_total_latency_ms']}ms")
    print(f"\n  Results saved to: {output_path}")

    driver.close()
    return metrics, output_path


if __name__ == "__main__":
    ids = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else None
    run_experiments(ids)
