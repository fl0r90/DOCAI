import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "supersecret_dgx_password")

class GraphService:
    def __init__(self):
        try:
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        except Exception as e:
            print(f"[!] Eroare conectare Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def sync_document_to_graph(self, doc_id: int, filename: str, case_id: int, extracted_data: dict, master_id: int = None):
        """Maprează documentul și relațiile sale specifice (Tranzacții, Contracte)."""
        if not self.driver: return

        doc_type = extracted_data.get("doc_type")
        metadata = extracted_data.get("metadata", {})

        with self.driver.session() as session:
            # 1. Noduri de bază (Case și Document)
            session.execute_write(self._create_base_nodes, case_id, doc_id, filename, master_id)

            # 2. Logică specializată pe tip de document
            if doc_type == "FACTURA":
                # Tranzacție: Furnizor -> Client
                f = metadata.get("furnizor", {})
                c = metadata.get("client", {})
                if f.get("nume") and c.get("nume"):
                    session.execute_write(self._create_transaction, 
                        f["nume"], f.get("cui"), 
                        c["nume"], c.get("cui"), 
                        metadata.get("total", 0), "FACTURA", doc_id
                    )

            elif doc_type == "OP":
                # Tranzacție: Plătitor -> Beneficiar
                p = metadata.get("platitor", {})
                b = metadata.get("beneficiar", {})
                if p.get("nume") and b.get("nume"):
                    session.execute_write(self._create_transaction, 
                        p["nume"], p.get("iban"), 
                        b["nume"], b.get("iban"), 
                        metadata.get("suma", 0), "ORDIN_PLATA", doc_id
                    )

            elif doc_type == "CONTRACT":
                parti = metadata.get("parti", [])
                for p in parti:
                    if p.get("nume"):
                        session.execute_write(self._create_entity_relationship, doc_id, p["nume"], p.get("cui"), p.get("rol", "PARTE"))

    @staticmethod
    def _create_base_nodes(tx, case_id, doc_id, filename, master_id):
        # Nodul Dosar (Case)
        tx.run("""
            MERGE (c:Case {id: $case_id})
            ON CREATE SET c.master_id = $master_id, c.created_at = datetime()
            ON MATCH SET c.master_id = $master_id
        """, case_id=case_id, master_id=master_id)
        
        # Nodul Document
        tx.run("""
            MERGE (d:Document {id: $doc_id})
            ON CREATE SET d.filename = $filename, d.created_at = datetime()
            WITH d
            MATCH (c:Case {id: $case_id})
            MERGE (d)-[:PARTE_DIN]->(c)
        """, doc_id=doc_id, filename=filename, case_id=case_id)

    @staticmethod
    def _create_transaction(tx, from_name, from_id, to_name, to_id, amount, t_type, doc_id):
        """Creează un flux financiar între două entități."""
        # Nod Sursă (Firma/Entitate)
        tx.run("MERGE (e1:Firma {name: $name}) ON CREATE SET e1.cui = $ext", name=from_name, ext=from_id)
        # Nod Destinație
        tx.run("MERGE (e2:Firma {name: $name}) ON CREATE SET e2.cui = $ext", name=to_name, ext=to_id)
        # Relația de Tranzacție
        tx.run("""
            MATCH (e1:Firma {name: $f_name}), (e2:Firma {name: $t_name}), (d:Document {id: $d_id})
            MERGE (e1)-[r:A_PLATIT {suma: $amt, tip: $type}]->(e2)
            MERGE (e1)-[:APARE_IN]->(d)
            MERGE (e2)-[:APARE_IN]->(d)
        """, f_name=from_name, t_name=to_name, amt=amount, type=t_type, d_id=doc_id)

    @staticmethod
    def _create_entity_relationship(tx, doc_id, nume, cui, rol):
        label = "Firma" if cui and len(str(cui)) > 5 else "Persoana"
        tx.run(f"""
            MERGE (e:{label} {{name: $nume}})
            ON CREATE SET e.cui = $cui
            WITH e
            MATCH (d:Document {{id: $doc_id}})
            MERGE (e)-[:APARE_IN {{rol: $rol}}]->(d)
        """, nume=nume, cui=cui, doc_id=doc_id, rol=rol)

graph_service = GraphService()
