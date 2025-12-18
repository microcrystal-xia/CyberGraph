#!/bin/bash
set -e

echo "=== CyberGraph Demo Setup ==="
echo ""

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Error: Docker is required but not installed."; exit 1; }
command -v docker compose >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1 || { echo "Error: Docker Compose is required but not installed."; exit 1; }

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "[1/4] Starting Neo4j and n8n services..."
docker compose up -d

echo "[2/4] Waiting for Neo4j to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
until curl -sf http://localhost:7474 > /dev/null 2>&1; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "Error: Neo4j failed to start after ${MAX_RETRIES} retries"
    exit 1
  fi
  echo "  Waiting for Neo4j... (attempt ${RETRY_COUNT}/${MAX_RETRIES})"
  sleep 3
done
echo "  Neo4j is ready."

echo "[3/4] Loading infrastructure graph..."
cat neo4j/init-graph.cypher | docker exec -i cybergraph-neo4j cypher-shell -u neo4j -p cybergraph123

# Verify graph loaded
NODE_COUNT=$(docker exec cybergraph-neo4j cypher-shell -u neo4j -p cybergraph123 "MATCH (n) RETURN count(n) AS count;" 2>/dev/null | tail -1 | tr -d '[:space:]')
echo "  Graph loaded: ${NODE_COUNT} nodes created."

echo "[4/4] Importing n8n workflows..."
# Wait for n8n to be ready
until curl -sf http://localhost:5678/healthz > /dev/null 2>&1; do
  sleep 2
done

# Import workflows via n8n REST API
curl -sf -X POST "http://localhost:5678/rest/workflows" \
  -H "Content-Type: application/json" \
  -d @n8n/cybergraph-query.json > /dev/null 2>&1 && echo "  Query workflow imported." || echo "  Note: Import query workflow manually via n8n UI."

curl -sf -X POST "http://localhost:5678/rest/workflows" \
  -H "Content-Type: application/json" \
  -d @n8n/cybergraph-remediate.json > /dev/null 2>&1 && echo "  Remediation workflow imported." || echo "  Note: Import remediation workflow manually via n8n UI."

echo ""
echo "=== Setup Complete ==="
echo ""
echo "  Neo4j Browser:  http://localhost:7474  (neo4j / cybergraph123)"
echo "  n8n Editor:     http://localhost:5678"
echo "  Query Webhook:  POST http://localhost:5678/webhook/cybergraph"
echo "  Remediate Hook: POST http://localhost:5678/webhook/cybergraph/remediate"
echo ""
echo "Test with:"
echo "  curl -X POST http://localhost:5678/webhook/cybergraph \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"query\": \"What services are affected by Log4Shell?\"}'"
