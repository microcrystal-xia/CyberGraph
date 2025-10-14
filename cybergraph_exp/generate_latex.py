"""Generate LaTeX tables from experiment results."""
import json
from collections import defaultdict
from pathlib import Path
from .config import Config

CATEGORY_LABELS = {
    "simple_lookup": "Simple Lookup",
    "filtered_query": "Filtered Query",
    "impact_analysis": "Impact Analysis",
    "blast_radius": "Blast Radius",
    "multi_hop": "Multi-hop Traversal",
    "aggregate": "Aggregate",
    "negative": "Negative (no result)",
}


def find_latest_results() -> Path:
    """Find the most recent experiment results file."""
    results_dir = Config.RESULTS_DIR
    files = sorted(results_dir.glob("experiment_*.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No experiment results found in {results_dir}")
    return files[-1]


def generate_results_table(results_path: Path = None) -> str:
    """Generate LaTeX table for Text-to-Cypher evaluation results."""
    if results_path is None:
        results_path = find_latest_results()

    with open(results_path) as f:
        data = json.load(f)

    results = data["results"]
    by_cat = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Text-to-Cypher evaluation: accuracy and latency by query category (using GPT-4o, $n=" + str(len(results)) + r"$).}",
        r"\label{tab:results}",
        r"\small",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabular}{@{}lccccc@{}}",
        r"\toprule",
        r"\textbf{Category} & \textbf{N} & \textbf{Syntax} & \textbf{Exec} & \textbf{Correct} & \textbf{Latency} \\",
        r" & & \textbf{\%} & \textbf{\%} & \textbf{\%} & \textbf{(ms)} \\",
        r"\midrule",
    ]

    totals = {"n": 0, "syntax": 0, "exec": 0, "correct": 0, "latency": 0}

    for cat in [
        "simple_lookup", "filtered_query", "impact_analysis",
        "blast_radius", "multi_hop", "aggregate", "negative",
    ]:
        items = by_cat.get(cat, [])
        if not items:
            continue
        n = len(items)
        syntax = 100 * sum(r["syntax_valid"] for r in items) / n
        exec_s = 100 * sum(r["exec_success"] for r in items) / n
        correct = 100 * sum(r["result_correct"] for r in items) / n
        latency = sum(r["total_latency_ms"] for r in items) / n

        label = CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
        lines.append(
            f"{label} & {n} & {syntax:.0f} & {exec_s:.0f} & {correct:.0f} & {latency:.0f} \\\\"
        )

        totals["n"] += n
        totals["syntax"] += sum(r["syntax_valid"] for r in items)
        totals["exec"] += sum(r["exec_success"] for r in items)
        totals["correct"] += sum(r["result_correct"] for r in items)
        totals["latency"] += sum(r["total_latency_ms"] for r in items)

    # Total row
    n = totals["n"]
    if n > 0:
        lines.append(r"\midrule")
        lines.append(
            f"\\textbf{{Overall}} & {n} "
            f"& {100*totals['syntax']/n:.0f} "
            f"& {100*totals['exec']/n:.0f} "
            f"& {100*totals['correct']/n:.0f} "
            f"& {totals['latency']/n:.0f} \\\\"
        )

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(lines)


def generate_all(results_path: Path = None):
    """Generate all LaTeX artifacts and write to results/tables.tex."""
    table = generate_results_table(results_path)

    output_path = Config.RESULTS_DIR / "tables.tex"
    output_path.write_text(table)
    print(f"LaTeX table written to {output_path}")
    return output_path


if __name__ == "__main__":
    generate_all()
