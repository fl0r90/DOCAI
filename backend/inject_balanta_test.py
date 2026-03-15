import sys
import os
from datetime import datetime

# Adăugăm calea pentru importuri
sys.path.append('/app')

from core_engine.database import ForensicSessionLocal
from core_engine import models

def inject_mismatch_data():
    db = ForensicSessionLocal()
    try:
        # 1. Creăm Case-ul pentru test
        case = models.Case(
            name="Analiza Discrepante Balanta Septembrie 2018",
            description="Investigatie automata pentru detectarea neconcordantelor intre balanta de verificare si facturile emise/primite.",
            status="OPEN"
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        print(f"[+] Case creat: ID {case.id}")

        # 2. Adaugam Balanta (ca document de referinta)
        balanta_doc = models.Document(
            filename="Balanta_sintetica-analitica.png",
            file_hash="hash_balanta_001",
            case_id=case.id,
            doc_type="BALANTA",
            status="COMPLETED",
            issue_date="30.09.2018",
            ai_summary="Balanta de verificare pentru perioada 01/09/2018-30/09/2018. Rulaj cumulat credit cont 704: 111,969.58 RON."
        )
        db.add(balanta_doc)
        db.flush()

        # 3. Adaugam Entitatile
        # Furnizorul fictiv care "umfla" veniturile
        furnizor = models.MasterEntity(
            official_name="TOP SERVICES SRL",
            cui_cif_cnp="RO987654321",
            address="Str. Business Center 10, Bucuresti",
            entity_type="FIRMA"
        )
        # Clientul (Firma noastra, subiectul balantei)
        client = models.MasterEntity(
            official_name="FIRMA NOASTRA SA",
            cui_cif_cnp="RO12345678",
            address="Sediul Social, Oras",
            entity_type="FIRMA"
        )
        db.add(furnizor)
        db.add(client)
        db.flush()

        # 4. Adaugam 2 Facturi care sa dea un total diferit de cel din balanta
        # Factura 1: 100,000 RON
        f1 = models.Document(
            filename="Factura_Servicii_TS001.pdf",
            file_hash="hash_factura_001",
            case_id=case.id,
            doc_type="FACTURA",
            status="COMPLETED",
            issue_date="10.09.2018",
            ai_summary="Factura servicii consultanta management."
        )
        db.add(f1)
        db.flush()
        
        db.add(models.FinancialItem(
            document_id=f1.id,
            doc_number="TS001",
            description="Servicii consultanta management septembrie",
            amount=100000.0,
            currency="RON"
        ))
        db.add(models.DocumentEntityLink(document_id=f1.id, entity_id=furnizor.id, role="FURNIZOR"))
        db.add(models.DocumentEntityLink(document_id=f1.id, entity_id=client.id, role="CLIENT"))

        # Factura 2: 150,000 RON
        f2 = models.Document(
            filename="Factura_Servicii_TS002.pdf",
            file_hash="hash_factura_002",
            case_id=case.id,
            doc_type="FACTURA",
            status="COMPLETED",
            issue_date="20.09.2018",
            ai_summary="Factura servicii dezvoltare software."
        )
        db.add(f2)
        db.flush()

        db.add(models.FinancialItem(
            document_id=f2.id,
            doc_number="TS002",
            description="Servicii dezvoltare software - etapa 2",
            amount=150000.0,
            currency="RON"
        ))
        db.add(models.DocumentEntityLink(document_id=f2.id, entity_id=furnizor.id, role="FURNIZOR"))
        db.add(models.DocumentEntityLink(document_id=f2.id, entity_id=client.id, role="CLIENT"))

        db.commit()
        print(f"[!] Succes: Balanta si 2 facturi injectate. Total facturi cont 704 (servicii): 250,000 RON.")
        print(f"[!] Balanta raporta pentru 704 doar 111,969.58 RON. Discrepanta: 138,030.42 RON.")
        print(f"[!] Case ID: {case.id}")

    except Exception as e:
        db.rollback()
        print(f"[-] Eroare la injectare: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inject_mismatch_data()
