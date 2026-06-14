
import os
import requests
import json
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://forensic_admin:supersecret_dgx_password@db:5432/forensic_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_full_rerank_diagnostic(user_question, case_id):
    print(f"[*] DIAGNOSTIC FULL RERANK pentru Case {case_id}...")
    
    with SessionLocal() as db:
        # Luam TOATE fragmentele din documentele cazului
        res = db.execute(text("""
            SELECT id, content_text, raw_metadata->>'chunk_index' as idx, raw_metadata->>'filename' as fname
            FROM document_storage
            WHERE raw_metadata->>'filename' IN (SELECT filename FROM documents WHERE case_id = :cid)
        """), {"cid": case_id}).fetchall()
        
        candidates = []
        for r in res:
            candidates.append({"id": str(r[0]), "content": r[1], "idx": r[2], "fname": r[3]})
        
        print(f"[*] Analizam {len(candidates)} fragmente cu BGE-Reranker...")
        
        from sentence_transformers import CrossEncoder
        reranker = CrossEncoder('BAAI/bge-reranker-base', cache_folder='/app/ocr_cache/reranker', device='cpu')
        
        # Perechi (intrebare, fragment)
        pairs = [[user_question, c["content"]] for c in candidates]
        scores = reranker.predict(pairs)
        
        for i in range(len(scores)):
            candidates[i]["score"] = float(scores[i])
            
        candidates.sort(key=lambda x: x["score"], reverse=True)
        
        print("\n--- TOP 5 FRAGMENTE DUPA RERANKER ---")
        for i, c in enumerate(candidates[:5]):
            print(f"{i+1}. [Index: {c['idx']}] Score: {c['score']:.4f} | Source: {c['fname']}")
            snippet = c['content'][:150].replace('\n', ' ')
            print(f"   Snippet: {snippet}...")
            if "30.099" in c['content']:
                print("   [!!!] GASIT CIFRA CORECTA!")

if __name__ == "__main__":
    q = "Care este valoarea exacta a 'Imobilizarilor corporale' la 31 decembrie 2023 din Situatia Pozitiei Financiare?"
    test_full_rerank_diagnostic(q, 5)
