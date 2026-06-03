from neo4j import GraphDatabase
import os

class GraphService:
    def __init__(self):
        self.driver = None
        self._connect()
    
    def _connect(self):
        """Connect to Neo4j database"""
        try:
            # Use environment variables for connection details
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            user = os.getenv("NEO4J_USER", "neo4j")
            password = os.getenv("NEO4J_PASSWORD", "password")
            
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
        except Exception as e:
            print(f"[!] Neo4j connection error: {e}")
    
    def process_case_documents(self, case_data):
        """Process documents in a case to create graph relationships"""
        if not self.driver:
            print("[!] Neo4j driver not initialized")
            return
            
        with self.driver.session() as session:
            # Create or update the case node
            case_id = case_data["id"]
            session.run("""
                MERGE (c:Case {id: $case_id})
                SET c.title = $title, c.description = $description
            """, case_id=case_id, title=case_data["title"], description=case_data["description"])
            
            # Process each document in the case
            for doc in case_data.get("documents", []):
                self._process_document(session, doc, case_id)
    
    def _process_document(self, tx, doc_data, case_id):
        """Process a single document to extract transaction data"""
        # This is a simplified version - in reality you'd parse the OCR results
        # or extract transaction data from the document content
        
        # For now, we'll just create a basic structure
        tx.run("""
            MERGE (d:Document {id: $doc_id})
            SET d.name = $doc_name, d.content = $content
            MERGE (c:Case {id: $case_id})
            MERGE (d)-[:PART_OF]->(c)
        """, doc_id=doc_data["id"], doc_name=doc_data["name"], 
               content=doc_data.get("content", ""), case_id=case_id)
    
    def query_relationships(self, entity_names: list):
        """Search for connections between entities mentioned."""
        if not self.driver or not entity_names: return ""
        
        results = []
        with self.driver.session() as session:
            for name in entity_names:
                # 1. Search for the node and documents where it appears
                query_docs = """
                MATCH (e)-[:APARE_IN]->(d:Document)
                WHERE e.name = $entity_name
                RETURN d.name AS document_name
                """
                result = session.run(query_docs, entity_name=name)
                for record in result:
                    results.append(f"Entity '{name}' found in document: {record['document_name']}")
            
            # 2. Search for relationships between entities
            query_relationships = """
            MATCH (e1)-[r]->(e2)
            WHERE e1.name IN $entity_names AND e2.name IN $entity_names
            RETURN e1.name AS source, e2.name AS target, r.type AS relationship_type
            """
            result = session.run(query_relationships, entity_names=entity_names)
            for record in result:
                results.append(f"Relationship: {record['source']} -> {record['target']} ({record['relationship_type']})")
        
        return results

# Create a global instance
graph_service = GraphService()
