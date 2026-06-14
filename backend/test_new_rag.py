
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

def simulate_new_hybrid_rag(case_id, user_question):
    print(f"[*] Testing NEW Hybrid RAG for Case {case_id}...")
    
    query_vec = _generate_query_vector(user_question)
    
    with SessionLocal() as db:
        doc_res = db.execute(text("SELECT id, filename FROM documents WHERE case_id = :case_id"), {"case_id": case_id}).fetchall()
        doc_ids = [r[0] for r in doc_res]
        parent_uuids = [uuid.uuid5(uuid.NAMESPACE_DNS, f"doc_{did}") for did in doc_ids]

        all_relevant_chunks = {}

        # 1. Vector Search
        if query_vec:
            vector_query = text("""
                SELECT id, content_text, raw_metadata->>'filename' as filename, embedding <=> CAST(:vec AS vector) as dist
                FROM document_storage
                WHERE parent_doc_id = ANY(:uuids)
                ORDER BY embedding <=> CAST(:vec AS vector)
                LIMIT 15
            """)
            res = db.execute(vector_query, {"vec": query_vec, "uuids": parent_uuids}).fetchall()
            for r in res:
                cid = str(r[0])
                all_relevant_chunks[cid] = {"content": r[1], "source": r[2], "score": 1.0}

        # --- NEW LOGIC: STOP-WORDS ---
        ro_stop_words = {"care", "este", "sunt", "pentru", "prin", "conform", "acest", "aceasta", "acești", "acele", "dintre", "catre", "acesta", "aceasta", "dupa", "fost", "unde", "daca", "cand"}
        search_terms = [w.strip(",.!?\"").lower() for w in user_question.split() if len(w) > 3 and w.strip(",.!?\"").lower() not in ro_stop_words]
        print(f"[*] Extracted terms (filtered): {search_terms}")

        # --- NEW LOGIC: COMBINED MULTI-TERM (AND) ---
        if len(search_terms) >= 2:
            print("[*] Running Multi-Term AND Search...")
            for i in range(len(search_terms)-1):
                term1, term2 = search_terms[i], search_terms[i+1]
                kw_query = text("""
                    SELECT id, content_text, raw_metadata->>'filename' as filename
                    FROM document_storage
                    WHERE parent_doc_id = ANY(:uuids) 
                    AND content_text ILIKE :t1 AND content_text ILIKE :t2
                    LIMIT 10
                """)
                kw_res = db.execute(kw_query, {"uuids": parent_uuids, "t1": f"%{term1}%", "t2": f"%{term2}%"}).fetchall()
                for r in kw_res:
                    cid = str(r[0])
                    if cid in all_relevant_chunks: 
                        all_relevant_chunks[cid]["score"] += 10.0
                        print(f"  [AND] Bonus +10.0 for '{term1}+{term2}' | Source: {r[2]}")
                    else: 
                        all_relevant_chunks[cid] = {"content": r[1], "source": r[2], "score": 10.0}
                        print(f"  [AND] New match '{term1}+{term2}' | Source: {r[2]}")

        # 2. Individual Keyword Search
        for term in search_terms[:8]:
            kw_query = text("""
                SELECT id, content_text, raw_metadata->>'filename' as filename
                FROM document_storage
                WHERE parent_doc_id = ANY(:uuids) AND content_text ILIKE :term
                LIMIT 5
            """)
            kw_res = db.execute(kw_query, {"uuids": parent_uuids, "term": f"%{term}%"}).fetchall()
            for r in kw_res:
                cid = str(r[0])
                if cid in all_relevant_chunks:
                    all_relevant_chunks[cid]["score"] += 3.0
                else:
                    all_relevant_chunks[cid] = {"content": r[1], "source": r[2], "score": 3.0}

        # Final Sort
        sorted_chunks = sorted(all_relevant_chunks.values(), key=lambda x: x["score"], reverse=True)
        print("\n--- TOP 5 FINAL CHUNKS (NEW LOGIC) ---")
        for i, chunk in enumerate(sorted_chunks[:5]):
            print(f"{i+1}. Source: {chunk['source']} (Score: {chunk['score']})")
            snippet = chunk['content'][:250].replace('\n', ' ')
            print(f"   Content Snippet: {snippet}...")

if __name__ == "__main__":
    q = "Conform situației consolidate a veniturilor, care este diferența dintre 'Venituri din vânzări' și 'Total venituri din vânzări și alte venituri' pentru anul 2023 și explică din ce este compusă această diferență conform notelor din document."
    simulate_new_hybrid_rag(5, q)
