#!/usr/bin/env python3
"""
Injectează cele 3 documente de test în Cazul 12 (Agroterra) și monitorizează procesarea lor prin worker.
"""

import os
import hashlib
import time
from core_engine.database import ForensicSessionLocal
from core_engine import models

CASE_ID = 12
UPLOADS_DIR = "/app/uploads"
USER_ID = 1

files_to_inject = [
    "CTR-2024-005_Contract_Furnizare_Seminte_si_Tratamente_AGRO-DISTRIB.pdf",
    "ACT-2024-05_Act_Aditional_1_CTR-2024-005_Preturi_si_Penalitati.pdf",
    "ACT-2024-06_Act_Aditional_2_CTR-2024-005_Discount_Retroactiv_Imputatie.pdf"
]

db = ForensicSessionLocal()
injected_ids = []

try:
    for filename in files_to_inject:
        file_path = os.path.join(UPLOADS_DIR, filename)
        if not os.path.exists(file_path):
            print(f"[!] Fișierul nu există: {file_path}")
            continue

        with open(file_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        existing = db.query(models.Document).filter(
            models.Document.case_id == CASE_ID,
            models.Document.filename == filename
        ).first()

        if existing:
            print(f"[*] Document existent găsit: ID {existing.id} ({filename}) - resetăm status la QUEUED.")
            existing.status = "QUEUED"
            existing.file_hash = file_hash
            existing.ai_summary = None
            db.commit()
            injected_ids.append((existing.id, filename))
        else:
            new_doc = models.Document(
                filename=filename,
                file_hash=file_hash,
                file_path=file_path,
                case_id=CASE_ID,
                user_id=USER_ID,
                status="QUEUED"
            )
            db.add(new_doc)
            db.commit()
            db.refresh(new_doc)
            print(f"[+] Adăugat în QUEUE: ID {new_doc.id} ({filename})")
            injected_ids.append((new_doc.id, filename))

    print(f"\n[*] Urmărim progresul procesării pentru documentele: {injected_ids}")
finally:
    db.close()
