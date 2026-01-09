# CyberGraph Demo Video Script

**Duration:** 3 minutes
**Format:** Dual-screen (Neo4j Browser left, Chat interface right)
**Resolution:** 1920x1080 minimum

---

## 0:00–0:30 — Introduction

**Visual:** Full infrastructure graph in Neo4j Browser, slowly rotating.

**Narration:**
"CyberGraph is a conversational threat intelligence agent for web infrastructure.
It represents servers, microservices, libraries, and CVEs as a knowledge graph
in Neo4j, and allows security operators to query impact chains using natural language."

**Action:** Highlight different node types (blue=Server, green=Microservice, yellow=Library, red=CVE).

---

## 0:30–1:15 — Scenario 1: CVE Impact Discovery

**Visual:** Chat interface appears on right panel.

**Operator types:** "I just saw news about Log4Shell, are we affected?"

**Action:** Show query being processed:
1. Natural language → Text-to-Cypher translation
2. Neo4j graph highlights the impact path (CVE → log4j → payment-service, notification-service)
3. Response appears in chat with CRITICAL alert

**Expected response:**
```
🚨 CRITICAL: 2 services directly affected by CVE-2021-44228 (CVSS 10.0)

Affected:
├── payment-service (PCI-scoped!) — via log4j-core 2.14.1
│   └── reachable from user-portal [3 hops]
└── notification-service — via log4j-core 2.14.1

Type "confirm isolate payment-service" to execute.
```

---

## 1:15–1:45 — Scenario 2: Deep Dive

**Operator types:** "Show me the payment service dependency chain"

**Action:** Neo4j Browser highlights full path:
`user-portal → auth-service → payment-service → log4j-core → CVE-2021-44228`

**Narration:** "The graph reveals that user-portal, our externally-exposed web service, is transitively affected through a 3-hop dependency chain — something a traditional scanner would miss."

---

## 1:45–2:15 — Scenario 3: Risk Assessment

**Operator types:** "What's the blast radius if auth-service is compromised?"

**Action:** Neo4j highlights connected subgraph from auth-service.

**Response shows:** All upstream and downstream services affected, servers involved, PCI scope warnings.

---

## 2:15–2:45 — Scenario 4: Remediation

**Operator types:** "confirm isolate payment-service"

**Action sequence:**
1. Firewall rule animation (DENY 10.0.2.1:8080)
2. Neo4j node for payment-service changes color to red
3. Status property updates to "quarantined"
4. Confirmation message with timestamp

**Expected response:**
```
✅ Remediation executed at 14:32:07 UTC
• Firewall rule: DENY 10.0.2.1:8080
• payment-service marked as [QUARANTINED]
• 3 upstream services affected
```

---

## 2:45–3:00 — Conclusion

**Visual:** Return to full graph view showing quarantined node.

**Narration:**
"CyberGraph demonstrates the Agentic Web paradigm — AI agents that observe,
reason about, and act upon web infrastructure topology. From natural language
query to confirmed remediation in under 10 seconds."

**Show:** Project URL and QR code.

---

## Post-Production Notes

- Add captions for each scenario title
- Include CyberGraph logo watermark (top-right)
- Export: MP4, H.264, 1080p
- Recording tool: OBS Studio recommended
