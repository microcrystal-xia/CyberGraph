"""Neo4j graph setup, initialization, and validation."""
import re
from pathlib import Path
from neo4j import GraphDatabase
from .config import Config

GRAPH_SCRIPT = Config.NEO4J_DIR / "init-graph.cypher"

EXPECTED_COUNTS = {
    "nodes": 14,
    "edges": 16,
    "Server": 3,
    "Microservice": 5,
    "Library": 4,
    "CVE": 2,
}


def get_driver():
    """Create and return a Neo4j driver instance."""
    return GraphDatabase.driver(
        Config.NEO4J_URI, auth=(Config.NEO4J_USER, Config.NEO4J_PASSWORD)
    )


def clear_graph(driver):
    """Remove all nodes and relationships."""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")


def init_graph(driver):
    """Execute the init-graph.cypher script to create the demo topology."""
    script = GRAPH_SCRIPT.read_text()
    # Split on semicolons, handling comments correctly
    statements = [s.strip() for s in script.split(";") if s.strip()]
    with driver.session() as session:
        for stmt in statements:
            # Skip pure comment blocks
            lines = [l for l in stmt.split("\n") if l.strip() and not l.strip().startswith("//")]
            if lines:
                session.run(stmt)


def validate_graph(driver) -> dict:
    """Validate graph matches expected topology. Returns validation dict."""
    with driver.session() as session:
        node_count = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        edge_count = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]

        # Per-label counts
        label_counts = {}
        for label in ("Server", "Microservice", "Library", "CVE"):
            count = session.run(
                f"MATCH (n:{label}) RETURN count(n) AS c"
            ).single()["c"]
            label_counts[label] = count

    valid = (
        node_count == EXPECTED_COUNTS["nodes"]
        and edge_count == EXPECTED_COUNTS["edges"]
    )

    return {
        "nodes": node_count,
        "edges": edge_count,
        "label_counts": label_counts,
        "valid": valid,
        "expected": EXPECTED_COUNTS,
    }


def reset_and_validate(driver) -> dict:
    """Clear, reinitialize, and validate the graph. Returns validation dict."""
    clear_graph(driver)
    init_graph(driver)
    result = validate_graph(driver)
    if not result["valid"]:
        raise RuntimeError(
            f"Graph validation failed: got {result['nodes']} nodes "
            f"(expected {EXPECTED_COUNTS['nodes']}), "
            f"{result['edges']} edges (expected {EXPECTED_COUNTS['edges']})"
        )
    return result


def run_query_file(driver, query_file: str, params: dict = None) -> list:
    """Execute a .cypher query file and return results."""
    path = Config.NEO4J_DIR / "queries" / query_file
    cypher = path.read_text()
    # Remove comment lines for execution
    lines = [l for l in cypher.split("\n") if not l.strip().startswith("//")]
    cypher_clean = "\n".join(lines).strip()
    with driver.session() as session:
        result = session.run(cypher_clean, params or {})
        return [dict(record) for record in result]
