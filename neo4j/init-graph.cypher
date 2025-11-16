// CyberGraph Demo - Infrastructure Topology Initialization
// Run this script to create the full demo graph in Neo4j

// Clear existing data for idempotent runs
MATCH (n) DETACH DELETE n;

// Create constraints for data integrity
CREATE CONSTRAINT server_name IF NOT EXISTS FOR (s:Server) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT microservice_name IF NOT EXISTS FOR (m:Microservice) REQUIRE m.name IS UNIQUE;
CREATE CONSTRAINT cve_id IF NOT EXISTS FOR (c:CVE) REQUIRE c.id IS UNIQUE;

// Create Servers
CREATE (s1:Server {name: 'web-server-01', ip: '10.0.1.1', os: 'Ubuntu 22.04', tier: 'frontend'})
CREATE (s2:Server {name: 'app-server-01', ip: '10.0.2.1', os: 'CentOS 7', tier: 'backend'})
CREATE (s3:Server {name: 'db-server-01', ip: '10.0.3.1', os: 'Ubuntu 20.04', tier: 'data'})

// Create Microservices
CREATE (ms1:Microservice {name: 'user-portal', exposed: true, lang: 'Node.js', version: '3.2.0', status: 'active'})
CREATE (ms2:Microservice {name: 'auth-service', exposed: false, lang: 'Java', version: '2.1.0', status: 'active'})
CREATE (ms3:Microservice {name: 'payment-service', exposed: false, lang: 'Java', version: '1.8.0', pci_scope: true, status: 'active'})
CREATE (ms4:Microservice {name: 'order-service', exposed: false, lang: 'Python', version: '4.0.1', status: 'active'})
CREATE (ms5:Microservice {name: 'notification-service', exposed: false, lang: 'Java', version: '1.2.0', status: 'active'})

// Create Libraries
CREATE (lib1:Library {name: 'log4j-core', version: '2.14.1', language: 'Java'})
CREATE (lib2:Library {name: 'spring-boot', version: '2.5.0', language: 'Java'})
CREATE (lib3:Library {name: 'express', version: '4.18.0', language: 'Node.js'})
CREATE (lib4:Library {name: 'requests', version: '2.26.0', language: 'Python'})

// Create CVEs
CREATE (cve1:CVE {id: 'CVE-2021-44228', name: 'Log4Shell', cvss: 10.0, description: 'Remote code execution via JNDI injection in log4j', published: '2021-12-10', severity: 'CRITICAL'})
CREATE (cve2:CVE {id: 'CVE-2022-22965', name: 'Spring4Shell', cvss: 9.8, description: 'RCE in Spring MVC via data binding', published: '2022-03-31', severity: 'CRITICAL'})

// Create Relationships - HOSTED_ON
CREATE (ms1)-[:HOSTED_ON]->(s1)
CREATE (ms2)-[:HOSTED_ON]->(s2)
CREATE (ms3)-[:HOSTED_ON]->(s2)
CREATE (ms4)-[:HOSTED_ON]->(s2)
CREATE (ms5)-[:HOSTED_ON]->(s2)

// Create Relationships - DEPENDS_ON (service-to-service)
CREATE (ms1)-[:DEPENDS_ON]->(ms2)
CREATE (ms1)-[:DEPENDS_ON]->(ms4)
CREATE (ms2)-[:DEPENDS_ON]->(ms3)

// Create Relationships - DEPENDS_ON (service-to-library)
CREATE (ms1)-[:DEPENDS_ON]->(lib3)
CREATE (ms2)-[:DEPENDS_ON]->(lib2)
CREATE (ms3)-[:DEPENDS_ON]->(lib1)
CREATE (ms3)-[:DEPENDS_ON]->(lib2)
CREATE (ms4)-[:DEPENDS_ON]->(lib4)
CREATE (ms5)-[:DEPENDS_ON]->(lib1)

// Create Relationships - HAS_VULNERABILITY
CREATE (lib1)-[:HAS_VULNERABILITY]->(cve1)
CREATE (lib2)-[:HAS_VULNERABILITY]->(cve2);
