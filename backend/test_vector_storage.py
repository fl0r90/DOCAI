import os
import uuid
import sys
from sqlalchemy import text
from core_engine.database import ForensicSessionLocal, forensic_engine
from core_engine.models import DocumentStorage, ForensicBase
from core_engine.services.storage_service import upsert_document_chunk

# Add current path to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

def verify_storage():
    # 0. Ensure Tables Exist
    print("[*] Verificam tabelele...")
    ForensicBase.metadata.create_all(bind=forensic_engine)
    print("[+] Tabelele (inclusiv document_storage) asigurate.")

    db = ForensicSessionLocal()
    try:
        # 1. Verify Extension
        print("[*] Verificam extensia pgvector...")
        res = db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).fetchone()
        if res:
            print(f"[+] Extensia '{res[0]}' este activa.")
        else:
            print("[!] Extensia 'vector' NU este activa in forensic_db.")
            return

        # 2. Test Upsert
        print("[*] Testam upsert_document_chunk...")
        parent_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        
        chunk_data = {
            "id": chunk_id,
            "parent_doc_id": parent_id,
            "content": "Acesta este un text de test pentru Docling si pgvector.",
            "metadata": {
                "source": "test_file.pdf",
                "page": 1,
                "docling_meta": {"version": "2.0.0"}
            },
            "extra": {"author": "AI Assistant"}
        }
        
        # Dummy vector of 1024 dims
        dummy_vector = [0.1] * 1024
        
        upsert_document_chunk(db, chunk_data, dummy_vector)
        print(f"[+] Chunk {chunk_id} inserat cu succes.")
        
        # 3. Verify Retrieval & Similarity Search
        print("[*] Testam cautarea prin similaritate...")
        # <=> is cosine distance
        query_vector = [0.11] * 1024
        results = db.query(DocumentStorage).order_by(DocumentStorage.embedding.l2_distance(query_vector)).limit(1).all()
        
        if results and str(results[0].id) == chunk_id:
            print(f"[+] Rezultat gasit prin similaritate! ID: {results[0].id}")
            print(f"[+] Continut: {results[0].content_text}")
        else:
            print("[!] Cautarea prin similaritate nu a returnat rezultatul asteptat.")

        # 4. Verify JSONB Querying
        print("[*] Testam interogarea JSONB...")
        meta_query = db.query(DocumentStorage).filter(DocumentStorage.raw_metadata['extra']['author'].astext == 'AI Assistant').first()
        if meta_query and str(meta_query.id) == chunk_id:
            print(f"[+] Interogare JSONB reusita! Author: {meta_query.raw_metadata['extra']['author']}")
        else:
            print("[!] Interogarea JSONB a esuat.")

    except Exception as e:
        print(f"[!] Eroare in timpul verificarii: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_storage()
