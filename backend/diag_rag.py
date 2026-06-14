
import os
import requests
import json
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://forensic_admin:supersecret_dgx_password@db:5432/forensic_db"
OLLAMA_URL = "http://llm:11434"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def _generate_query_vector(text_input):
    try:
        response = requests.post(f"{OLLAMA_URL}/api/embeddings", json={"model": "bge-m3", "prompt": text_input}, timeout=60)
        return response.json().get("embedding", [])
    except Exception as e:
        print(f"Embedding error: {e}")
        return []

def diagnostic_rag(case_id, user_question):
    print(f"[*] DIAGNOSTIC RAG pentru Case {case_id}...")
    print(f"[*] Intrebare: {user_question}")
    
    query_vec = _generate_query_vector(user_question)
    
    with SessionLocal() as db:
        # 1. Identificam documentele din caz
        doc_res = db.execute(text("SELECT id, filename FROM documents WHERE case_id = :case_id"), {"case_id": case_id}).fetchall()
        doc_ids = [r[0] for r in doc_res]
        parent_uuids = [uuid.uuid5(uuid.NAMESPACE_DNS, f"doc_{did}") for did in doc_ids]

        # 2. Cautare Hibrida (Vector + Keywords)
        all_relevant_chunks = {}

        # Vector Search
        if query_vec:
            vector_chunks = db.execute(text("""
                SELECT id, content_text, raw_metadata->>'filename' as filename, embedding <=> CAST(:vec AS vector) as dist
                FROM document_storage
                WHERE parent_doc_id = ANY(:uuids)
                ORDER BY dist ASC LIMIT 20
            """), {"vec": query_vec, "uuids": parent_uuids}).fetchall()
            
            for vc in vector_chunks:
                all_relevant_chunks[str(vc[0])] = {"content": vc[1], "source": vc[2], "score": 1.0, "dist": float(vc[3])}

        # Keyword Search (cu bonusul implementat)
        ro_stop_words = {"care", "este", "sunt", "pentru", "prin", "conform", "acest", "aceasta", "acești", "acele", "dintre", "catre", "acesta", "aceasta", "dupa", "fost", "unde", "daca", "unde", "cand"}
        search_terms = [w.strip(",.!?\"").lower() for w in user_question.split() if len(w) > 3 and w.strip(",.!?\"").lower() not in ro_stop_words]
        
        for term in search_terms:
            kw_res = db.execute(text("""
                SELECT id, raw_metadata->>'filename'
                FROM document_storage
                WHERE parent_doc_id = ANY(:uuids) AND content_text ILIKE :term
            """), {"uuids": parent_uuids, "term": f"%{term}%"}).fetchall()
            for r in kw_res:
                cid = str(r[0])
                if cid in all_relevant_chunks:
                    all_relevant_chunks[cid]["score"] += 3.0
                else:
                    all_relevant_chunks[cid] = {"source": r[1], "score": 3.0}

        # 3. Analiza TOP 10
        sorted_chunks = sorted(all_relevant_chunks.items(), key=lambda x: x[1]["score"], reverse=True)
        
        print("\n--- TOP 10 REZULTATE RAG ---")
        for i, (cid, data) in enumerate(sorted_chunks[:10]):
            content_snippet = data.get("content", "N/A")[:100].replace("\n", " ")
            print(f"{i+1}. [ID: {cid[:8]}] Score: {data['score']:.1f} | Source: {data['source']}")
            print(f"   Snippet: {content_snippet}...")
            if "30.099" in data.get("content", ""):
                print("   [!!!] GASIT! Fragmentul 94 este aici!")

if __name__ == "__main__":
    q = "Care este valoarea exacta a 'Imobilizarilor corporale' la 31 decembrie 2023 din Situatia Pozitiei Financiare?"
    diagnostic_rag(5, q)
