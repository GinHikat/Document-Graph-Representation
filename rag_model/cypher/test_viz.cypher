// Show all nodes and relationship in namespace Test1
MATCH (n:Test_rel_3)-[r]->(m:Test_rel_3)
RETURN n, r, m;
// LIMIT 200 if need to limit down to 200 nodes only

// Show nodes in Test_2
MATCH (n:Test_3)-[r]->(m:Test_3)
RETURN n, r, m;

// Show all nodes but relationship
MATCH (n)-[r]->(m)
RETURN n, r, m;

// Show Schema (Labels + relation type)
CALL db.schema.visualization();

// Delete from Namespace
MATCH (n: Test1)
DETACH DELETE n; 



