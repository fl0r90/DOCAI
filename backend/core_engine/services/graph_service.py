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
            self.create_constraints()
        except Exception as e:
            print(f"[!] Eroare conectare Neo4j: {e}")
            self.driver = None

    def create_constraints(self):
        if not self.driver: return
        with self.driver.session() as session:
            try:
                session.run("CREATE CONSTRAINT entitate_cui_unique IF NOT EXISTS FOR (e:Entitate) REQUIRE e.cui IS UNIQUE")
                session.run("CREATE CONSTRAINT cont_iban_unique IF NOT EXISTS FOR (c:Cont_Bancar) REQUIRE c.iban IS UNIQUE")
            except Exception as e:
                print(f"[*] Neo4j Constraints already exist or error: {e}")

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

        graph_payload = {
            "entitati": extracted_data.get("graph_data", {}).get("entitati", []) or extracted_data.get("entitati", []),
            "relatii": extracted_data.get("graph_data", {}).get("relatii", []) or extracted_data.get("relatii", []),
            "tranzactii": extracted_data.get("financial_data", []),
            "outline": extracted_data.get("outline", [])
        }

        if not any(graph_payload.values()):
            return

        with self.driver.session() as session:
            session.execute_write(self._insereaza_extractia_optimizata, doc_id, filename, case_id, graph_payload, master_id)

    @staticmethod
    def _insereaza_extractia_optimizata(tx, doc_id, nume_fisier, case_id, date_json, master_id):
        # 1. Ancora (Document & Case)
        tx.run("MERGE (c:Case {id: $case_id}) SET c.master_id = $m_id", case_id=case_id, m_id=master_id)
        tx.run("""
            MERGE (d:Document {doc_id: $doc_id})
            SET d.name = $nume_fisier, d.filename = $nume_fisier, d.case_id = $case_id
            WITH d
            MATCH (c:Case {id: $case_id})
            MERGE (d)-[:PARTE_DIN]->(c)
            """, doc_id=str(doc_id), nume_fisier=nume_fisier, case_id=case_id
        )

        # 1.1. Ierarhie Document (Pages)
        outline = date_json.get("outline", [])
        unique_pages = set()
        for item in outline:
            if "page" in item: unique_pages.add(int(item["page"]))
        
        # Extragem pagini si din entitati daca exista
        for ent in date_json.get("entitati", []):
            if "page" in ent: unique_pages.add(int(ent["page"]))

        for p_no in sorted(list(unique_pages)):
            tx.run("""
                MATCH (d:Document {doc_id: $doc_id})
                MERGE (p:Page {doc_id: $doc_id, page_no: $p_no})
                MERGE (d)-[:HAS_PAGE]->(p)
            """, doc_id=str(doc_id), p_no=p_no)

        # 2. Entități și Co-ocurență (Cine apare cu cine)
        entitati_per_pagina = {} # page_no -> [list of nodes]
        
        valori_entitati = {} 
        for idx, ent in enumerate(date_json.get("entitati", [])):
            val = ent.get("valoare")
            if not val or str(val).lower() == "none" or len(str(val)) < 2: 
                continue # Skip junk data
            
            tip = re.sub(r'[^A-Za-z0-9_]', '', ent.get("tip_entitate", "Entitate"))
            e_id = ent.get("id", f"e_{idx}")
            valori_entitati[e_id] = val
            p_no = ent.get("page")
            master_entity_id = ent.get("master_entity_id")

            # Logica de MERGE inteligenta: CUI > MasterID > Nume
            params = {"val": val, "doc_id": str(doc_id), "m_id": master_entity_id}
            
            if tip == "IBAN" or ent.get("tip_entitate") == "IBAN":
                query = "MERGE (e:Cont_Bancar {iban: $val}) SET e.name = $val"
            elif tip in ["Firma", "CUI", "Entitate"] or master_entity_id:
                if master_entity_id:
                    query = "MERGE (e:Entitate {master_id: $m_id}) SET e.name = $val"
                else:
                    # Incearca CUI, altfel Nume
                    query = "MERGE (e:Entitate {name: $val}) SET e.name = $val"
            else:
                query = f"MERGE (e:{tip} {{name: $val}}) SET e.name = $val"
            
            tx.run(query, **params)
            
            # Legare de Document
            tx.run(f"""
                MATCH (e {{name: $val}}) WHERE e:Cont_Bancar OR e:Entitate OR e:{tip}
                MATCH (d:Document {{doc_id: $doc_id}})
                MERGE (e)-[:APARE_IN]->(d)
                """, val=val, doc_id=str(doc_id))
            
            if p_no:
                tx.run(f"""
                    MATCH (e {{name: $val}}) WHERE e:Cont_Bancar OR e:Entitate OR e:{tip}
                    MATCH (p:Page {{doc_id: $doc_id, page_no: $p_no}})
                    MERGE (e)-[:SURSA_PAGINA]->(p)
                """, val=val, doc_id=str(doc_id), p_no=int(p_no))
                
                if p_no not in entitati_per_pagina: entitati_per_pagina[p_no] = []
                entitati_per_pagina[p_no].append(val)

        # 2.1. CO-OCURRENȚĂ (DOAR între entități diferite de tipuri importante, limitat)
        # Reducem zgomotul: nu mai legăm tot cu tot
        for p_no, entities in entitati_per_pagina.items():
            if len(entities) < 2 or len(entities) > 10: continue # Skip pagini prea aglomerate (zgomot)
            for i in range(len(entities)):
                for j in range(i + 1, len(entities)):
                    tx.run("""
                        MATCH (a {name: $val_a}), (b {name: $val_b})
                        WHERE a <> b
                        MERGE (a)-[r:PROXIMITATE]->(b)
                        SET r.count = coalesce(r.count, 0) + 1, r.doc_id = $doc_id
                    """, val_a=entities[i], val_b=entities[j], doc_id=str(doc_id))

        # 3. Relatii Semantice (Explicit extrase de LLM)
        for rel in date_json.get("relatii", []):
            tip_rel = re.sub(r'[^A-Za-z0-9_]', '', rel.get("tip_relatie", "ASOCIAT_CU")).upper()
            s_val = valori_entitati.get(rel.get("sursa"))
            d_val = valori_entitati.get(rel.get("destinatie"))
            if s_val and d_val:
                tx.run(f"""
                    MATCH (s {{name: $s_val}}), (d {{name: $d_val}})
                    MERGE (s)-[:{tip_rel}]->(d)
                """, s_val=s_val, d_val=d_val)

        # 4. Tranzactii Financiare (Trasabilitate BANI - Mix and Match)
        for tr in date_json.get("tranzactii", []):
            pg_id = tr.get("pg_id")
            if not pg_id: continue
            
            # Colectam orice identificator disponibil
            identifiers = []
            if tr.get("iban_source"): identifiers.append(("Cont_Bancar", "iban", tr["iban_source"], "SURSA"))
            if tr.get("cui_source"): identifiers.append(("Entitate", "cui", tr["cui_source"], "SURSA"))
            if tr.get("iban_destination"): identifiers.append(("Cont_Bancar", "iban", tr["iban_destination"], "DESTINATIE"))
            if tr.get("cui_destination"): identifiers.append(("Entitate", "cui", tr["cui_destination"], "DESTINATIE"))
            
            sources = [i for i in identifiers if i[3] == "SURSA"]
            dests = [i for i in identifiers if i[3] == "DESTINATIE"]
            
            for s_tip, s_key, s_val, _ in sources:
                for d_tip, d_key, d_val, _ in dests:
                    tx.run(f"""
                        MERGE (s:{s_tip} {{{s_key}: $s_val}})
                        MERGE (d:{d_tip} {{{d_key}: $d_val}})
                        
                        // 1. Direct relationship for compatibility
                        MERGE (s)-[r:TRANZACTIE {{id_sql: $pg_id}}]->(d)
                        SET r.suma = $suma, r.data = $data, r.desc = $desc, r.tip = $t_type
                        
                        // 2. Node representation for temporal graphing
                        MERGE (t:Transaction {{id: $pg_id}})
                        SET t.suma = $suma, t.data = $data, t.desc = $desc, t.case_id = $case_id
                        MERGE (s)-[:SENDER]->(t)
                        MERGE (t)-[:RECEIVER]->(d)
                    """, s_val=s_val, d_val=d_val, pg_id=pg_id, 
                         suma=tr.get("amount"), data=tr.get("transaction_date"), 
                         desc=tr.get("description"), t_type=tr.get("transaction_type"),
                         case_id=case_id)

        # 5. Chain transactions sequentially
        tx.run("""
            MATCH (t:Transaction {case_id: $case_id})
            WITH t ORDER BY t.data ASC
            WITH collect(t) as txs
            FOREACH (i in range(0, size(txs)-2) |
                FOREACH (t1 in [txs[i]] |
                    FOREACH (t2 in [txs[i+1]] |
                        MERGE (t1)-[:SUCCEDE]->(t2)
                    )
                )
            )
        """, case_id=case_id)

    def query_relationships(self, entity_names: list):
        """Caută conexiuni între entitățile menționate."""
        if not self.driver or not entity_names: return ""
        
        results = []
        with self.driver.session() as session:
            for name in entity_names:
                # 1. Căutăm nodul și documentele în care apare
                query_docs = """
                MATCH (e)-[:APARE_IN]->(d:Document)
                WHERE e.name = $name OR e.iban = $name
                RETURN coalesce(e.name, e.iban) as entitate, labels(e)[0] as tip, d.name as document
                """
                res_docs = session.run(query_docs, name=name)
                for record in res_docs:
                    results.append(f"Entitatea '{record['entitate']}' ({record['tip']}) apare în documentul: {record['document']}")

            # 2. Căutăm legături directe între oricare două entități din listă
            if len(entity_names) >= 2:
                query_rel = """
                MATCH (s)-[r]->(d)
                WHERE (s.name IN $names OR s.iban IN $names) AND (d.name IN $names OR d.iban IN $names)
                RETURN coalesce(s.name, s.iban) as sursa, type(r) as relatie, coalesce(d.name, d.iban) as destinatie
                """
                res_rel = session.run(query_rel, names=entity_names)
                for record in res_rel:
                    results.append(f"LEGĂTURĂ GĂSITĂ: {record['sursa']} --[{record['relatie']}]--> {record['destinatie']}")

        return "\n".join(results) if results else ""

    def get_entity_subgraph(self, entities: list, limit: int = 15):
        """Caută conexiuni de 1-hop și 2-hop în Neo4j pentru o listă de entități."""
        if not self.driver or not entities: return ""
        
        # Filtram entitatile nule/goale
        entities = [e for e in entities if e and len(str(e)) >= 2]
        if not entities: return ""
        
        results = []
        with self.driver.session() as session:
            query = """
            MATCH (e)-[r]->(neighbor)
            WHERE (e.name IN $entities OR e.iban IN $entities)
            RETURN coalesce(e.name, e.iban) as source, type(r) as relation, coalesce(neighbor.name, neighbor.iban) as target, labels(neighbor)[0] as type
            LIMIT $limit
            """
            try:
                res = session.run(query, entities=entities, limit=limit)
                for record in res:
                    results.append(f"RELAȚIE GRAF: {record['source']} --[{record['relation']}]--> {record['target']} ({record['type']})")
            except Exception as e:
                print(f"[!] Eroare Neo4j get_entity_subgraph: {e}")
                
        return "\n".join(results) if results else ""

graph_service = GraphService()
