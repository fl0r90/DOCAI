import sys
import os
import random
from datetime import datetime, timedelta

# Add backend to path to import models
sys.path.append('/home/cfp-90/AI/V2/backend')

from app.database import SessionLocal
from app import models

UPLOAD_DIR = "/app/uploads"

def inject_data():
    db = SessionLocal()
    try:
        # Asigurăm utilizator admin
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin:
            from app.core.security import get_password_hash
            admin = models.User(username="admin", hashed_password=get_password_hash("admin123"), role="ADMIN", needs_password_change=0)
            db.add(admin)
            db.commit()

        # 1. Asigurăm existența dosarului 1
        case = db.query(models.Case).filter(models.Case.id == 1).first()
        if not case:
            case = models.Case(id=1, name="Investigație Test 001", description="Dosar pentru testarea analizei cognitive")
            db.add(case)
            db.commit()
            db.refresh(case)

        firme_test = [
            {"nume": "SC CONSTRUCT TOTAL SRL", "cui": "RO11223344", "adr": "Str. Constructorilor 1, Ploiesti"},
            {"nume": "METALURGICA SA", "cui": "RO55667788", "adr": "Bld. Industriei 45, Galati"},
            {"nume": "SOFTWARE SOLUTIONS SRL", "cui": "RO99001122", "adr": "Str. Tehnologiei 10, Cluj-Napoca"},
            {"nume": "PRIMARIA MUNICIPIULUI TEST", "cui": "RO123456", "adr": "Piata Centrala 1, Oras"},
            {"nume": "OFFSHORE SECRETS LTD", "cui": "CY998877", "adr": "Limassol, Cyprus"}
        ]

        # 2. Generăm 10 facturi cu analize AI și ITEMI FINANCIARI
        for i in range(1, 11):
            is_risky = (i == 7 or i == 3)
            risk = random.randint(75, 98) if is_risky else random.randint(2, 15)
            
            furnizor_data = firme_test[4] if is_risky else random.choice(firme_test[:3])
            client_data = firme_test[3]
            
            filename = f"Proba_Fiscale_0{i}.pdf"
            
            # CREĂM FIȘIERUL PE DISK (DUMMY)
            file_path = os.path.join(UPLOAD_DIR, filename)
            with open(file_path, "w") as f:
                f.write(f"Acesta este un document de test generat automat: {filename}")

            summary = f"Factură de la {furnizor_data['nume']} pentru achiziție echipamente. "
            if is_risky:
                summary += "ALERTA: Entitate înregistrată în Cipru. Risc ridicat de evaziune sau spălare de bani."
                explanation = "Jurisdicție offshore. Sumă nejustificată pentru servicii de mentenanță."
            else:
                summary += "Tranzacție comercială obișnuită."
                explanation = "Furnizor local verificat."

            doc = models.Document(
                filename=filename,
                hash_sha256=f"hash_v4_{i}_{random.random()}",
                status="COMPLETED",
                case_id=case.id,
                doc_type="FACTURA",
                doc_number=f"DOC-2025-{i}",
                doc_date="24.02.2025",
                currency="RON",
                ai_summary=summary,
                risk_score=float(risk),
                risk_analysis=explanation
            )
            db.add(doc)
            db.flush()

            # Link Entities
            for f_data, rol in [(furnizor_data, "FURNIZOR"), (client_data, "CLIENT")]:
                ent = db.query(models.MasterEntity).filter(models.MasterEntity.official_name == f_data["nume"]).first()
                if not ent:
                    ent = models.MasterEntity(official_name=f_data["nume"], cui_cif_cnp=f_data["cui"], entity_type="FIRMA", address=f_data["adr"])
                    db.add(ent)
                    db.flush()
                db.add(models.DocumentEntityLink(document_id=doc.id, entity_id=ent.id, role=rol))

            # Adăugăm sume reale (financial items)
            total_sum = 0
            for _ in range(random.randint(1, 2)):
                amt = float(random.randint(50000, 150000)) if is_risky else float(random.randint(1000, 5000))
                total_sum += amt
                db.add(models.FinancialItem(
                    document_id=doc.id,
                    description="Servicii specializate" if is_risky else "Materiale constructii",
                    amount=amt,
                    currency="RON"
                ))
            
            doc.total_amount = total_sum

        db.commit()
        print(f"\n[!] Succes: 10 documente salvate în {UPLOAD_DIR} și în BD.")

    except Exception as e:
        db.rollback()
        print(f"[-] Eroare: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inject_data()