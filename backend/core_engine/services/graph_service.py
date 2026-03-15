import os
import re
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

    def delete_document(self, doc_id: int):
        if not self.driver: return
        with self.driver.session() as session:
            session.run("MATCH (d:Document) WHERE d.doc_id = $id OR d.id = $id_num DETACH DELETE d", 
                        id=str(doc_id), id_num=doc_id)
            session.run("MATCH (e) WHERE (e:Persoana OR e:Firma OR e:Telefon OR e:Crypto OR e:IBAN OR e:Entitate) AND NOT (e)--() DELETE e")

    def sync_document_to_graph(self, doc_id: int, filename: str, case_id: int, extracted_data: dict, master_id: int = None):
        if not self.driver: return
        self.delete_document(doc_id)

        date_graph = extracted_data.get("graph_data") 
        if not date_graph:
            date_graph = {
                "entitati": extracted_data.get("entitati", []),
                "relatii": extracted_data.get("relatii", [])
            }

        if not date_graph.get("entitati") and not date_graph.get("relatii"):
            return

        with self.driver.session() as session:
            session.execute_write(self._insereaza_extractia_optimizata, doc_id, filename, case_id, date_graph, master_id)

    @staticmethod
    def _insereaza_extractia_optimizata(tx, doc_id, nume_fisier, case_id, date_json, master_id):
        # 1. Ancora
        tx.run("MERGE (c:Case {id: $case_id}) SET c.master_id = $m_id", case_id=case_id, m_id=master_id)
        tx.run("""
            MERGE (d:Document {doc_id: $doc_id})
            SET d.name = $nume_fisier, d.filename = $nume_fisier, d.case_id = $case_id
            WITH d
            MATCH (c:Case {id: $case_id})
            MERGE (d)-[:PARTE_DIN]->(c)
            """, doc_id=str(doc_id), nume_fisier=nume_fisier, case_id=case_id
        )

        # 2. Entitati
        valori_entitati = {} 
        for ent in date_json.get("entitati", []):
            tip = re.sub(r'[^A-Za-z0-9_]', '', ent.get("tip_entitate", "Entitate"))
            val = ent.get("valoare")
            if not val or not ent.get("id"): continue
            valori_entitati[ent["id"]] = val
            
            # Adaugam si proprietatea 'name' pentru compatibilitate cu frontend-ul
            tx.run(f"MERGE (e:{tip} {{valoare: $val}}) SET e.name = $val, e.master_id = $m_id", val=val, m_id=master_id)
            # Legam de document
            tx.run(f"MATCH (e:{tip} {{valoare: $val}}), (d:Document {{doc_id: $doc_id}}) MERGE (e)-[:APARE_IN]->(d)", 
                   val=val, doc_id=str(doc_id))

        # 3. Relatii
        for rel in date_json.get("relatii", []):
            tip_rel = re.sub(r'[^A-Za-z0-9_]', '', rel.get("tip_relatie", "ASOCIAT_CU"))
            s_val = valori_entitati.get(rel.get("sursa"))
            d_val = valori_entitati.get(rel.get("destinatie"))
            if s_val and d_val:
                tx.run(f"""
                    MATCH (s {{valoare: $s_val}}), (d {{valoare: $d_val}})
                    MERGE (s)-[:{tip_rel}]->(d)
                """, s_val=s_val, d_val=d_val)

    def query_relationships(self, entity_names: list):
        """Caută conexiuni între entitățile menționate."""
        if not self.driver or not entity_names: return ""
        
        results = []
        with self.driver.session() as session:
            for name in entity_names:
                # 1. Căutăm nodul și documentele în care apare
                query_docs = """
                MATCH (e {valoare: $name})-[:APARE_IN]->(d:Document)
                RETURN e.valoare as entitate, labels(e)[0] as tip, d.name as document
                """
                res_docs = session.run(query_docs, name=name)
                for record in res_docs:
                    results.append(f"Entitatea '{record['entitate']}' ({record['tip']}) apare în documentul: {record['document']}")

            # 2. Căutăm legături directe între oricare două entități din listă
            if len(entity_names) >= 2:
                query_rel = """
                MATCH (s)-[r]->(d)
                WHERE s.valoare IN $names AND d.valoare IN $names
                RETURN s.valoare as sursa, type(r) as relatie, d.valoare as destinatie
                """
                res_rel = session.run(query_rel, names=entity_names)
                for record in res_rel:
                    results.append(f"LEGĂTURĂ GĂSITĂ: {record['sursa']} --[{record['relatie']}]--> {record['destinatie']}")

        return "\n".join(results) if results else ""

graph_service = GraphService()
