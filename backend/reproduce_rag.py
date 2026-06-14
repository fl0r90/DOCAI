
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

def _generate_query_vector(text):
    try:
        response = requests.post(f"{OLLAMA_URL}/api/embeddings", json={"model": "bge-m3", "prompt": text}, timeout=60)
        return response.json().get("embedding", [])
    except Exception as e:
        print(f"Embedding error: {e}")
        return []

def simulate_hybrid_rag(case_id, user_question):
    print(f"[*] Simulating Hybrid RAG for Case {case_id}...")
    print(f"[*] Question: {user_question}")
    
    query_vec = _generate_query_vector(user_question)
    if not query_vec:
        print("[!] No query vector generated!")
        return

    with SessionLocal() as db:
        # Get document IDs for the case
        doc_res = db.execute(text("SELECT id, filename FROM documents WHERE case_id = :case_id"), {"case_id": case_id}).fetchall()
        doc_ids = [r[0] for r in doc_res]
        docs_map = {r[0]: r[1] for r in doc_res}
        
        parent_uuids = [uuid.uuid5(uuid.NAMESPACE_DNS, f"doc_{did}") for did in doc_ids]
        print(f"[*] Searching across {len(doc_ids)} documents...")

        all_relevant_chunks = {}

        # 1. Vector Search
        # We need to use pgvector extension distance operator <=>
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
            all_relevant_chunks[cid] = {"content": r[1], "source": r[2], "score": 1.0, "dist": float(r[3])}
            print(f"  [V] Dist: {r[3]:.4f} | Source: {r[2]}")

        # 2. Keyword Search
        search_terms = [w.strip(",.!?\"").lower() for w in user_question.split() if len(w) > 3]
        for term in search_terms[:5]:
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
                    print(f"  [K+] Bonus 3.0 for '{term}' | Source: {r[2]}")
                else:
                    all_relevant_chunks[cid] = {"content": r[1], "source": r[2], "score": 3.0}
                    print(f"  [K] New match for '{term}' | Source: {r[2]}")

        # Final Sort
        sorted_chunks = sorted(all_relevant_chunks.values(), key=lambda x: x["score"], reverse=True)
        print("\n--- TOP 5 FINAL CHUNKS ---")
        for i, chunk in enumerate(sorted_chunks[:5]):
            print(f"{i+1}. Source: {chunk['source']} (Score: {chunk['score']})")
            print(f"   Content: {chunk['content'][:200]}...")

if __name__ == "__main__":
    q = "Conform situației consolidate a veniturilor, care este diferența dintre 'Venituri din vânzări' și 'Total venituri din vânzări și alte venituri' pentru anul 2023 și explică din ce este compusă această diferență conform notelor din document."
    simulate_hybrid_rag(5, q)
