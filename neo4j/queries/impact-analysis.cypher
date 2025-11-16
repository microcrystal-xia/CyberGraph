// Find all services affected by a specific CVE
// Parameter: $cveId (e.g., 'CVE-2021-44228')
MATCH path = (cve:CVE {id: $cveId})<-[:HAS_VULNERABILITY]-(lib:Library)
             <-[:DEPENDS_ON*1..5]-(svc:Microservice)
RETURN svc.name AS service,
       svc.pci_scope AS pci_scope,
       svc.exposed AS exposed,
       length(path) AS dependency_depth,
       [node IN nodes(path) | node.name] AS chain,
       cve.cvss AS cvss_score,
       cve.name AS cve_name
ORDER BY dependency_depth;
