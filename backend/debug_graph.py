
import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "supersecret_dgx_password")

def debug_neo4j():
    print("=== DEBUG NEO4J STATUS ===")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            # 1. Numar noduri per label
            print("\n[1] Noduri per Tip:")
            res = session.run("MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC")
            for r in res:
                print(f"    - {r['label']}: {r['count']}")
                
            # 2. Numar relatii per tip
            print("\n[2] Relatii per Tip:")
            res = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(*) as count ORDER BY count DESC")
            for r in res:
                print(f"    - {r['type']}: {r['count']}")
                
            # 3. Top noduri conectate (Hubs)
            print("\n[3] Top 5 Noduri (Cele mai multe legaturi):")
            res = session.run("MATCH (n)-[r]-() RETURN n.name as name, count(r) as connections ORDER BY connections DESC LIMIT 5")
            for r in res:
                print(f"    - {r['name']}: {r['connections']} legaturi")

        driver.close()
    except Exception as e:
        print(f"Eroare: {e}")

if __name__ == "__main__":
    debug_neo4j()
