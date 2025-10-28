"""End-to-end pipeline tests for CyberGraph.

Requires:
- Neo4j running at bolt://localhost:7687 (via docker compose)
- LLM API key configured in .env

Run: pytest cybergraph_exp/tests/ -v
"""
import json
import pytest
from pathlib import Path

from cybergraph_exp.config import Config
from cybergraph_exp.graph_setup import get_driver, reset_and_validate, validate_graph
from cybergraph_exp.text_to_cypher import translate, validate_cypher_syntax
from cybergraph_exp.impact_analysis import (
    execute_cypher,
    analyze_cve_impact,
    calculate_risk_level,
    get_blast_radius,
    simulate_remediation,
)


@pytest.fixture(scope="module")
def driver():
    """Shared Neo4j driver for all tests in this module."""
    d = get_driver()
    yield d
    d.close()


@pytest.fixture(autouse=True)
def reset_graph(driver):
    """Reset graph before each test."""
    reset_and_validate(driver)


# ── Graph Setup Tests ────────────────────────────────────────────

class TestGraphSetup:
    def test_neo4j_connection(self, driver):
        with driver.session() as s:
            result = s.run("RETURN 1 AS n").single()
        assert result["n"] == 1

    def test_graph_node_count(self, driver):
        v = validate_graph(driver)
        assert v["nodes"] == 14

    def test_graph_edge_count(self, driver):
        v = validate_graph(driver)
        assert v["edges"] == 16

    def test_graph_label_counts(self, driver):
        v = validate_graph(driver)
        assert v["label_counts"]["Server"] == 3
        assert v["label_counts"]["Microservice"] == 5
        assert v["label_counts"]["Library"] == 4
        assert v["label_counts"]["CVE"] == 2

    def test_graph_validation_passes(self, driver):
        v = validate_graph(driver)
        assert v["valid"] is True


# ── Cypher Query Tests ───────────────────────────────────────────

class TestCypherQueries:
    def test_impact_analysis_log4shell(self, driver):
        rows, ok, _, _ = execute_cypher(
            driver,
            "MATCH path = (cve:CVE {id: 'CVE-2021-44228'})<-[:HAS_VULNERABILITY]-(lib:Library)"
            "<-[:DEPENDS_ON*1..5]-(svc:Microservice) "
            "RETURN svc.name AS service ORDER BY service",
        )
        assert ok
        services = [r["service"] for r in rows]
        assert "payment-service" in services
        assert "notification-service" in services

    def test_blast_radius_query(self, driver):
        rows, ok, _, _ = execute_cypher(
            driver,
            "MATCH (target:Microservice {name: 'auth-service'})"
            "<-[:DEPENDS_ON*1..5]-(affected:Microservice) "
            "RETURN affected.name AS service",
        )
        assert ok
        assert any(r["service"] == "user-portal" for r in rows)

    def test_dependency_audit_query(self, driver):
        rows, ok, _, _ = execute_cypher(
            driver,
            "MATCH (svc:Microservice)-[:HOSTED_ON]->(srv:Server {name: 'app-server-01'}) "
            "RETURN svc.name AS service ORDER BY service",
        )
        assert ok
        assert len(rows) == 4

    def test_negative_query_no_cve_on_db_server(self, driver):
        rows, ok, _, _ = execute_cypher(
            driver,
            "MATCH (s:Server {name: 'db-server-01'})<-[:HOSTED_ON]-(svc:Microservice)"
            "-[:DEPENDS_ON*1..5]->(lib:Library)-[:HAS_VULNERABILITY]->(cve:CVE) "
            "RETURN svc.name AS service",
        )
        assert ok
        assert len(rows) == 0


# ── Impact Analysis Tests ────────────────────────────────────────

class TestImpactAnalysis:
    def test_log4shell_impact(self, driver):
        result = analyze_cve_impact(driver, "CVE-2021-44228")
        assert result["count"] >= 2
        assert "payment-service" in result["affected_services"]
        assert "notification-service" in result["affected_services"]
        assert result["risk_level"] == "CRITICAL"
        assert result["has_pci_scope"] is True

    def test_spring4shell_impact(self, driver):
        result = analyze_cve_impact(driver, "CVE-2022-22965")
        assert result["count"] >= 2
        assert "auth-service" in result["affected_services"]
        assert result["risk_level"] in ("CRITICAL", "HIGH")

    def test_nonexistent_cve(self, driver):
        result = analyze_cve_impact(driver, "CVE-FAKE-99999")
        assert result["count"] == 0

    def test_risk_level_critical(self):
        assert calculate_risk_level(2, 10.0, True, False) == "CRITICAL"
        assert calculate_risk_level(1, 9.5, False, True) == "CRITICAL"

    def test_risk_level_high(self):
        assert calculate_risk_level(3, 5.0, False, False) == "HIGH"
        assert calculate_risk_level(1, 7.5, False, False) == "HIGH"

    def test_risk_level_medium(self):
        assert calculate_risk_level(1, 5.0, False, False) == "MEDIUM"

    def test_risk_level_low(self):
        assert calculate_risk_level(1, 2.0, False, False) == "LOW"

    def test_risk_level_info(self):
        assert calculate_risk_level(0, 0, False, False) == "INFO"


# ── Blast Radius Tests ───────────────────────────────────────────

class TestBlastRadius:
    def test_auth_service_blast(self, driver):
        result = get_blast_radius(driver, "auth-service")
        assert "user-portal" in result["upstream_services"]

    def test_payment_service_blast(self, driver):
        result = get_blast_radius(driver, "payment-service")
        upstream = result["upstream_services"]
        assert "auth-service" in upstream or "user-portal" in upstream


# ── Remediation Tests ────────────────────────────────────────────

class TestRemediation:
    def test_quarantine_service(self, driver):
        result = simulate_remediation(driver, "payment-service", "test-op")
        assert result["success"] is True
        assert result["new_status"] == "quarantined"

    def test_quarantine_nonexistent(self, driver):
        result = simulate_remediation(driver, "nonexistent-service", "test-op")
        assert result["success"] is False


# ── Text-to-Cypher Tests (requires LLM API) ─────────────────────

class TestTextToCypher:
    """These tests call the LLM API. Mark as slow."""

    @pytest.mark.slow
    def test_simple_query_generation(self):
        cypher, latency = translate("List all servers")
        assert validate_cypher_syntax(cypher)
        assert latency > 0

    @pytest.mark.slow
    def test_impact_query_generation(self):
        cypher, latency = translate("What services are affected by Log4Shell?")
        assert validate_cypher_syntax(cypher)
        assert "CVE-2021-44228" in cypher or "Log4Shell" in cypher.lower() or "log4" in cypher.lower()

    def test_validate_read_query(self):
        assert validate_cypher_syntax("MATCH (n:Server) RETURN n.name ORDER BY n.name")

    def test_reject_destructive_query(self):
        assert not validate_cypher_syntax("MATCH (n) DELETE n")
        assert not validate_cypher_syntax("CREATE (n:Test {name: 'x'}) RETURN n")
        assert not validate_cypher_syntax("MATCH (n) SET n.x = 1 RETURN n")
