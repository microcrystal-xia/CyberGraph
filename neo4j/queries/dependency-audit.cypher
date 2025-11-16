// Audit services on a specific server with vulnerability status
// Parameter: $serverName (e.g., 'app-server-01')
MATCH (svc:Microservice)-[:HOSTED_ON]->(srv:Server {name: $serverName})
OPTIONAL MATCH (svc)-[:DEPENDS_ON*1..3]->(lib:Library)-[:HAS_VULNERABILITY]->(cve:CVE)
RETURN svc.name AS service,
       svc.lang AS language,
       svc.version AS version,
       svc.status AS status,
       collect(DISTINCT {library: lib.name, lib_version: lib.version, cve_id: cve.id, cvss: cve.cvss, severity: cve.severity}) AS vulnerabilities
ORDER BY svc.name;
