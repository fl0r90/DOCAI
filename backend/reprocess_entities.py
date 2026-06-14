
import os
import sys
import json
import requests
import re
from sqlalchemy import text
sys.path.append('/app')

from core_engine.database import SessionLocal
from core_engine.models import Document, DocumentChunk, MasterEntity, DocumentEntityLink
from core_engine.services.graph_service import graph_service

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434")
TARGET_DOCS = [22, 16, 24, 18, 19, 17, 23, 20, 21, 25]

def extract_entities_from_text(text_content):
    prompt = f"""
    ESTI UN ANALIST FORENSIC. Extrage toate entitatile (FIRME si PERSOANE) si RELATIILE dintre ele din textul de mai jos.
    Text: \"\"\"{text_content[:4000]}\"\"\"
    
    RETURN UN JSON VALID:
    {{
      \"entitati\": [
        {{\"nume\": \"NUME COMPLET\", \"tip\": \"FIRMA/PERSOANA\", \"rol\": \"ADMINISTRATOR/ASOCIAT/CLIENT/FURNIZOR\"}}
      ],
      \"relatii\": [
        {{\"sursa\": \"NUME SURSA\", \"destinatie\": \"NUME DESTINATIE\", \"tip\": \"ADMINISTREAZA/DETINE/AFILIAT\"}}
      ]
    }}
    FARA EXPLICATII, DOAR JSON.
    """
    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": "gemma4:e4b",
            "prompt": prompt,
            "stream": False
        }, timeout=120)
        content = r.json().get("response", "{}")
        # Curatam JSON-ul daca LLM-ul pune ```json ... ```
        clean_json = re.search(r'\{.*\}', content, re.DOTALL)
        if clean_json:
            return json.loads(clean_json.group())
        return json.loads(content)
    except Exception as e:
        print(f"Eroare LLM: {e} | Content: {r.text[:100] if 'r' in locals() else 'N/A'}")
        return {}

def reprocess():
    print(f"=== [REPROCESS ENTITIES] TARGET: {len(TARGET_DOCS)} DOCS ===")
    db = SessionLocal()
    
    for doc_id in TARGET_DOCS:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc: continue
        
        print(f"[*] Procesare: {doc.filename}...")
        
        # Luam primele 2 chunk-uri (sunt de ajuns pentru ONRC/Contracte sa vedem partile)
        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.page_number).limit(3).all()
        full_text = " ".join([c.content for c in chunks])
        
        data = extract_entities_from_text(full_text)
        
        # Injectam in SQL
        for ent in data.get("entitati", []):
            name = ent.get("nume")
            if not name or len(name) < 3: continue
            
            # 1. Master Entity
            me = db.query(MasterEntity).filter(MasterEntity.official_name == name).first()
            if not me:
                me = MasterEntity(official_name=name, entity_type=ent.get("tip", "FIRMA"))
                db.add(me)
                db.commit()
                db.refresh(me)
            
            # 2. Link
            link = db.query(DocumentEntityLink).filter(DocumentEntityLink.document_id == doc_id, DocumentEntityLink.entity_id == me.id).first()
            if not link:
                link = DocumentEntityLink(document_id=doc_id, entity_id=me.id, role=ent.get("rol"))
                db.add(link)
        
        db.commit()
        
        # Sincronizam cu Neo4j (folosim serviciul existent)
        # Ne asiguram ca graph_payload e in formatul asteptat de GraphService
        graph_data = {
            "entitati": [{"valoare": e.get("nume"), "tip_entitate": e.get("tip"), "rol": e.get("rol"), "page": 1} for e in data.get("entitati", [])],
            "relatii": [{"sursa_val": r.get("sursa"), "dest_val": r.get("destinatie"), "tip_relatie": r.get("tip")} for r in data.get("relatii", [])]
        }
        
        # Adaptam formatul pentru graph_service._insereaza_extractia_optimizata (care foloseste 'sursa' ca index in valori_entitati)
        # Dar pentru simplitate, folosim un script Cypher direct pentru relatii
        with graph_service.driver.session() as session:
            for r in data.get("relatii", []):
                session.run("""
                    MERGE (s {name: $s_name})
                    MERGE (d {name: $d_name})
                    WITH s, d
                    CALL apoc.create.relationship(s, $tip, {}, d) YIELD rel
                    RETURN rel
                """, s_name=r.get("sursa"), d_name=r.get("destinatie"), tip=r.get("tip", "LEGAT_DE").replace(" ", "_").upper())

    db.close()
    print("\n=== [REPROCESS COMPLETED] REFRESH GRAPH NOW ===")

if __name__ == "__main__":
    reprocess()
    # Rulam si sincronizarea finala de Case
    os.system("python3 repair_graph_master.py")
