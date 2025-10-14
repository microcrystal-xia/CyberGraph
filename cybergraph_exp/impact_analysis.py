"""Impact analysis: execute Cypher, score risk, compute blast radius."""
import time
from pathlib import Path
from .config import Config

_QUERIES_DIR = Config.NEO4J_DIR / "queries"


def execute_cypher(driver, cypher: str, params: dict = None) -> tuple:
    """Execute a Cypher query and return (rows, success, error, latency_ms)."""
    start = time.perf_counter()
    try:
        with driver.session() as session:
            result = session.run(cypher, params or {})
            rows = [dict(record) for record in result]
        latency_ms = (time.perf_counter() - start) * 1000
        return rows, True, "", latency_ms
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return [], False, str(e), latency_ms


def _load_query(filename: str) -> str:
    """Load a .cypher file, stripping comment lines."""
    text = (_QUERIES_DIR / filename).read_text()
    lines = [l for l in text.split("\n") if not l.strip().startswith("//")]
    return "\n".join(lines).strip()


def analyze_cve_impact(driver, cve_id: str) -> dict:
    """Run impact analysis for a given CVE ID."""
    cypher = _load_query("impact-analysis.cypher")
    rows, success, error, latency_ms = execute_cypher(
        driver, cypher, {"cveId": cve_id}
    )

    if not success:
        return {"cve_id": cve_id, "error": error, "count": 0, "latency_ms": latency_ms}

    affected = [r["service"] for r in rows]
    has_pci = any(r.get("pci_scope") for r in rows)
    has_exposed = any(r.get("exposed") for r in rows)
    max_cvss = max((r.get("cvss_score", 0) for r in rows), default=0)
    risk = calculate_risk_level(len(affected), max_cvss, has_pci, has_exposed)

    return {
        "cve_id": cve_id,
        "affected_services": affected,
        "count": len(affected),
        "max_cvss": max_cvss,
        "has_pci_scope": has_pci,
        "has_exposed": has_exposed,
        "risk_level": risk,
        "chains": [r.get("chain") for r in rows],
        "latency_ms": latency_ms,
    }


def calculate_risk_level(
    service_count: int, max_cvss: float, has_pci: bool, has_exposed: bool
) -> str:
    """Assign risk level based on CVSS, scope, and exposure."""
    if max_cvss >= 9.0 and (has_pci or has_exposed):
        return "CRITICAL"
    if max_cvss >= 7.0 or service_count >= 3:
        return "HIGH"
    if max_cvss >= 4.0:
        return "MEDIUM"
    if service_count > 0:
        return "LOW"
    return "INFO"


def get_blast_radius(driver, service_name: str) -> dict:
    """Find upstream services affected if a service is compromised."""
    cypher = _load_query("blast-radius.cypher")
    rows, success, error, latency_ms = execute_cypher(
        driver, cypher, {"serviceName": service_name}
    )

    if not success or not rows:
        return {"service": service_name, "error": error or "not found", "latency_ms": latency_ms}

    row = rows[0]
    return {
        "service": service_name,
        "upstream_services": row.get("upstream_services", []),
        "downstream_dependencies": row.get("downstream_dependencies", []),
        "server": row.get("hosting_server"),
        "server_ip": row.get("server_ip"),
        "latency_ms": latency_ms,
    }


def simulate_remediation(driver, service_name: str, operator: str = "test") -> dict:
    """Quarantine a service in the graph and verify the update."""
    # Set status to quarantined
    update_cypher = (
        "MATCH (s:Microservice {name: $name}) "
        "SET s.status = 'quarantined', s.quarantined_by = $operator "
        "RETURN s.name AS name, s.status AS status"
    )
    rows, success, error, latency_ms = execute_cypher(
        driver, update_cypher, {"name": service_name, "operator": operator}
    )

    if not success or not rows:
        return {"success": False, "error": error or "service not found"}

    # Verify
    verify_rows, _, _, _ = execute_cypher(
        driver,
        "MATCH (s:Microservice {name: $name}) RETURN s.status AS status",
        {"name": service_name},
    )

    return {
        "success": True,
        "service": service_name,
        "new_status": verify_rows[0]["status"] if verify_rows else "unknown",
        "operator": operator,
        "latency_ms": latency_ms,
    }
