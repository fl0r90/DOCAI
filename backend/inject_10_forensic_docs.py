#!/usr/bin/env python3
"""
Injectează cele 10 documente criminalistice în Cazul 12 (Agroterra)
și monitorizează progresul procesării prin v2-worker.
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
    "PROCES_VERBAL_ANAF_Antifrauda_Control_Inopinat_Octombrie_2024.pdf",
    "DECIZIE_IMPUNERE_ANAF_Nr_88204_Noiembrie_2024.pdf",
    "EXTRAS_BANCAR_ING_Nordic_Consulting_Management_Iulie_2024.pdf",
    "CONTRACT_IMPRUMUT_ASOCIAT_Nordic_Consulting_GeorgeCostea_2023.pdf",
    "EXPORT_CHAT_WHATSAPP_RaduTeodorescu_AvocatPopa_Octombrie2024.pdf",
    "RAPORT_ACTIVITATE_Nordic_Consulting_Factura_NOR-2024-0095.pdf",
    "PROCES_VERBAL_CONSTATARE_DIFERENTE_Siloz_Braila_18_Iunie_2024.pdf",
    "NOTA_CONTABILA_REGULARIZARE_STOC_NC-2024-0618.pdf",
    "ADRESA_BANCA_TRANSILVANIA_Audit_Garantii_Credit_Noiembrie_2024.pdf",
    "RAPORT_AUDIT_INTERN_INVENTAR_ANUAL_Decembrie_2024.pdf"
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
            existing.doc_metadata = None
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

    print(f"\n[+] Total documente injectate cu succes în Cazul {CASE_ID}: {len(injected_ids)}")
finally:
    db.close()
