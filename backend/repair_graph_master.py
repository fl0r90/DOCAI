
import os
import sys
from sqlalchemy import text
sys.path.append('/app')

from core_engine.database import SessionLocal
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "supersecret_dgx_password")

def sync_perfect_graph(case_id=5):
    print(f"=== [PERFECT SYNC] CASE {case_id} ===")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with SessionLocal() as db:
        # Luăm datele din SQL pentru a asigura sincronizarea perfectă
        sql_case = db.execute(text("SELECT id, name FROM cases WHERE id = :id"), {"id": case_id}).fetchone()
        sql_docs = db.execute(text("SELECT id, filename FROM documents WHERE case_id = :id"), {"id": case_id}).fetchall()
        
        with driver.session() as session:
            # 1. Cream Case-ul
            session.run("MERGE (c:Case {id: $id}) SET c.name = $name", id=sql_case[0], name=sql_case[1])
            
            for doc_id, filename in sql_docs:
                # 2. Cream Documentele cu ID numeric (cum vrea API-ul)
                print(f"    [*] Sincronizare Doc: {filename} (ID: {doc_id})")
                session.run("""
                    MERGE (d:Document {id: $id})
                    SET d.filename = $name, d.name = $name, d.case_id = $case_id
                    WITH d
                    MATCH (c:Case {id: $case_id})
                    MERGE (d)-[:PARTE_DIN]->(c)
                """, id=doc_id, name=filename, case_id=case_id)
                
                # 3. Luăm entitățile legate de acest document din SQL
                sql_entities = db.execute(text("""
                    SELECT e.official_name, e.entity_type 
                    FROM master_entities e
                    JOIN document_entity_links l ON e.id = l.entity_id
                    WHERE l.document_id = :doc_id
                """), {"doc_id": doc_id}).fetchall()
                
                for e_name, e_type in sql_entities:
                    label = "Firma" if e_type == "FIRMA" else "Persoana"
                    session.run(f"""
                        MERGE (e:{label} {{name: $name}})
                        WITH e
                        MATCH (d:Document {{id: $doc_id}})
                        MERGE (e)-[:APARE_IN]->(d)
                    """, name=e_name, doc_id=doc_id)

    driver.close()
    print("\n=== [SYNC COMPLETED] REFRESH NOW! ===")

if __name__ == "__main__":
    sync_perfect_graph(5)
