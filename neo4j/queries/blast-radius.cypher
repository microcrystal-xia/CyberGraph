// Calculate blast radius from a compromised service
// Parameter: $serviceName (e.g., 'payment-service')
// Returns all nodes reachable from the compromised service via dependency and hosting relationships
MATCH (source:Microservice {name: $serviceName})
OPTIONAL MATCH upstream = (source)<-[:DEPENDS_ON*1..5]-(upstream_svc:Microservice)
OPTIONAL MATCH downstream = (source)-[:DEPENDS_ON*1..5]->(downstream_node)
OPTIONAL MATCH (source)-[:HOSTED_ON]->(srv:Server)
RETURN source.name AS compromised_service,
       collect(DISTINCT upstream_svc.name) AS upstream_services,
       collect(DISTINCT downstream_node.name) AS downstream_dependencies,
       srv.name AS hosting_server,
       srv.ip AS server_ip;
