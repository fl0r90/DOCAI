from neo4j import GraphDatabase
import os

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "supersecret_dgx_password")

def cleanup_and_fix_graph(case_id=2):
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        # 1. Ștergem toate nodurile IBAN (care aglomerează degeaba în acest moment)
        print("[*] Curățăm nodurile IBAN inutile...")
        session.run("MATCH (i:IBAN) DETACH DELETE i")

        # 2. Ștergem nodurile orfane (care nu au nicio relație)
        print("[*] Ștergem nodurile orfane...")
        session.run("MATCH (n) WHERE NOT (n)--() AND NOT n:Case DELETE n")

        # 3. Legăm TOP SERVICES SRL și Popescu Ion de Case-ul corect
        print("[*] Legăm entitățile de Case 2...")
        session.run("""
            MATCH (c:Case {id: $case_id})
            MERGE (f:Firma {valoare: 'TOP SERVICES SRL'})
            SET f.name = 'TOP SERVICES SRL'
            MERGE (p:Persoana {valoare: 'Popescu Ion'})
            SET p.name = 'Popescu Ion', p.functie = 'CONTABIL FIRMA AUDITATA'
            
            // Relația de conflict
            MERGE (f)-[r1:ASOCIAT_CU {tip: 'CONFLICT_INTERESE', risc: 'CRITIC'}]->(p)
            
            // Legăm de Case
            MERGE (f)-[:APARE_IN_CAZ]->(c)
            MERGE (p)-[:APARE_IN_CAZ]->(c)
            
            // Legăm de un document specific pentru a fi vizibil în contextul documentului
            MERGE (d:Document {doc_id: '102'})
            SET d.name = 'Factura_Servicii_TS001.pdf'
            MERGE (f)-[:APARE_IN]->(d)
            MERGE (p)-[:APARE_IN]->(d)
            MERGE (d)-[:PARTE_DIN]->(c)
        """, case_id=case_id)
        
        print("[+] Graful a fost curățat și entitățile au fost legate corect.")

    driver.close()

if __name__ == "__main__":
    cleanup_and_fix_graph()
