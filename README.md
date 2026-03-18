# CyberGraph

CyberGraph is a graph-driven security demo that helps you answer one question fast:

"If a vulnerable dependency is compromised, which business services are affected and what should we do next?"

It combines:
- Neo4j for infrastructure and dependency relationships
- n8n for automation workflows
- LLM prompts for natural-language-to-Cypher and impact summaries

## What this project includes

- Infrastructure graph seed data: `neo4j/init-graph.cypher`
- Ready-to-run Cypher queries: `neo4j/queries/`
- n8n workflows:
  - `n8n/cybergraph-query.json`
  - `n8n/cybergraph-remediate.json`
  - `n8n/cybergraph-reset.json`
- Prompt templates:
  - `n8n/prompts/text-to-cypher.md`
  - `n8n/prompts/impact-analysis.md`
- Python experiment utilities and tests: `cybergraph_exp/`
- One-command local bootstrap: `scripts/demo-setup.sh`

## Quick start

### 1) Prerequisites

- Docker + Docker Compose
- Bash shell

### 2) Start services and load demo data

```bash
./scripts/demo-setup.sh
```

After setup:
- Neo4j Browser: `http://localhost:7474` (`neo4j / cybergraph123`)
- n8n Editor: `http://localhost:5678`
- Query webhook: `POST http://localhost:5678/webhook/cybergraph`

### 3) Test with one request

```bash
curl -X POST http://localhost:5678/webhook/cybergraph \
  -H 'Content-Type: application/json' \
  -d '{"query": "What services are affected by Log4Shell?"}'
```

## Typical use cases

- Blast-radius analysis for CVEs across service dependency chains
- Dependency audit by host, runtime, or exposure
- Guided remediation workflows (isolation/reset) through n8n

## Project structure

```text
CyberGraph/
├── cybergraph_exp/            # experiment scripts and tests
├── demo/                      # demo UI
├── images/                    # demo screenshots
├── n8n/                       # exported n8n workflows and prompts
├── neo4j/                     # graph seed and query templates
├── scripts/                   # setup automation
├── docker-compose.yml
└── .env.example
```

## Security notes

- Do not commit real API keys into `.env`.
- This repository is for demo/research usage; review workflows before production use.

## License

If you plan to open-source this publicly, add a LICENSE file (for example MIT or Apache-2.0) before broader distribution.
