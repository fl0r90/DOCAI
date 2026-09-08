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
    
    @staticmethod
    def _entity_fields(e: dict):
        """Extrage (nume, tip, rol) dintr-un dict de entitate cu chei variate.
        Grinder-ul produce atât {valoare, tip_entitate, rol} (tabele) cât și
        {nume, tip, rol} (text), așa că le acceptăm pe ambele."""
        if not isinstance(e, dict):
            return None, None, None
        name = e.get("nume") or e.get("valoare") or e.get("name")
        etype = e.get("tip") or e.get("tip_entitate") or e.get("entity_type")
        role = e.get("rol") or e.get("role") or ""
        if name:
            name = str(name).strip()
        return (name or None), etype, role

    def sync_document_to_graph(self, doc_id, filename, case_id, doc_metadata, master_id=None):
        """Scrie documentul și entitățile extrase în Neo4j (folosit de worker)."""
        if not self.driver:
            print("[!] Neo4j driver indisponibil - sync graf sărit.")
            return

        graph_data = (doc_metadata or {}).get("graph_data", {}) or {}
        entitati = graph_data.get("entitati", []) or []
        relatii = graph_data.get("relatii", []) or []

        try:
            with self.driver.session() as session:
                session.run(
                    """
                    MERGE (d:Document {id: $doc_id})
                    SET d.name = $filename, d.case_id = $case_id, d.master_id = $master_id
                    MERGE (c:Case {id: $case_id})
                    MERGE (d)-[:PART_OF]->(c)
                    """,
                    doc_id=doc_id, filename=filename, case_id=case_id, master_id=master_id,
                )

                for e in entitati:
                    name, etype, role = self._entity_fields(e)
                    if not name:
                        continue
                    session.run(
                        """
                        MERGE (n:Entity {name: $name})
                        SET n.type = coalesce($etype, n.type), n.case_id = $case_id
                        WITH n
                        MATCH (d:Document {id: $doc_id})
                        MERGE (n)-[r:APARE_IN]->(d)
                        SET r.role = $role
                        """,
                        name=name, etype=etype, role=role, doc_id=doc_id, case_id=case_id,
                    )

                for rel in relatii:
                    src = rel.get("sursa") or rel.get("source")
                    dst = rel.get("destinatie") or rel.get("target")
                    rtype = rel.get("tip") or rel.get("type") or "RELATED"
                    if not src or not dst:
                        continue
                    session.run(
                        """
                        MERGE (a:Entity {name: $src})
                        MERGE (b:Entity {name: $dst})
                        MERGE (a)-[r:REL]->(b)
                        SET r.type = $rtype
                        """,
                        src=str(src).strip(), dst=str(dst).strip(), rtype=rtype,
                    )
        except Exception as ex:
            print(f"[!] Eroare sync_document_to_graph (doc {doc_id}): {ex}")

    def get_entity_subgraph(self, entity_names: list, limit: int = 10):
        """Returnează un sub-graf text pentru entitățile căutate (folosit de agent).
        Potrivire case-insensitive pe substring, ca să prindă variațiile de nume."""
        if not self.driver or not entity_names:
            return ""
        terms = [str(t).strip().lower() for t in entity_names if t and len(str(t).strip()) >= 3]
        if not terms:
            return ""

        lines = []
        try:
            with self.driver.session() as session:
                # 1. În ce documente apar entitățile potrivite
                docs = session.run(
                    """
                    MATCH (n:Entity)-[r:APARE_IN]->(d:Document)
                    WHERE any(term IN $terms WHERE toLower(n.name) CONTAINS term)
                    RETURN DISTINCT n.name AS entity, d.name AS document, r.role AS role
                    LIMIT $limit
                    """,
                    terms=terms, limit=limit,
                )
                for rec in docs:
                    role = f" (rol: {rec['role']})" if rec.get("role") else ""
                    lines.append(f"Entitatea '{rec['entity']}'{role} apare în: {rec['document']}")

                # 2. Relații directe între entitățile potrivite
                rels = session.run(
                    """
                    MATCH (a:Entity)-[r:REL]->(b:Entity)
                    WHERE any(term IN $terms WHERE toLower(a.name) CONTAINS term)
                       OR any(term IN $terms WHERE toLower(b.name) CONTAINS term)
                    RETURN a.name AS source, b.name AS target, r.type AS rel_type
                    LIMIT $limit
                    """,
                    terms=terms, limit=limit,
                )
                for rec in rels:
                    lines.append(f"Relație: {rec['source']} -[{rec['rel_type']}]-> {rec['target']}")
        except Exception as ex:
            print(f"[!] Eroare get_entity_subgraph: {ex}")
            return ""

        return "\n".join(lines)

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
