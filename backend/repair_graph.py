from sqlalchemy import create_engine, text
from core_engine.services.graph_service import graph_service
import os
import json

# DB
FORENSIC_URL = os.getenv("FORENSIC_DATABASE_URL", "postgresql://forensic_admin:supersecret_dgx_password@db:5432/forensic_db")
engine = create_engine(FORENSIC_URL)

def repair_graph_for_case(case_id):
    with engine.connect() as conn:
        docs = conn.execute(text("SELECT id, filename, doc_metadata FROM documents WHERE case_id = :cid"), {"cid": case_id}).fetchall()
        for doc_id, filename, metadata in docs:
            if metadata:
                print(f"[*] Reparam GRAF pentru {filename} (ID: {doc_id})...")
                # Folosim serviciul reparat
                graph_service.sync_document_to_graph(doc_id, filename, case_id, metadata)
                print(f"[+] Finalizat {filename}")

if __name__ == "__main__":
    repair_graph_for_case(5)
