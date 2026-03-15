import sys
import os
from sqlalchemy import text
from fpdf import FPDF

# Adăugăm calea pentru importuri
sys.path.append('/app')

from core_engine.database import ForensicSessionLocal, engine
from core_engine import models
from core_engine.services.graph_service import graph_service

def apply_db_upgrade():
    print("[*] Începere upgrade bază de date...")
    with engine.connect() as conn:
        try:
            # Adăugăm risk_score la cases dacă nu există
            conn.execute(text("ALTER TABLE cases ADD COLUMN IF NOT EXISTS risk_score FLOAT DEFAULT 0.0"))
            conn.execute(text("ALTER TABLE cases ADD COLUMN IF NOT EXISTS risk_explanation TEXT"))
            conn.commit()
            print("[+] Coloane de risc adăugate în tabelul 'cases'.")
        except Exception as e:
            print(f"[-] Eroare upgrade DB: {e}")

def inject_graph_conflict():
    print("[*] Injectare conflict de interese în Neo4j...")
    if not graph_service.driver:
        print("[-] Neo4j driver indisponibil.")
        return

    with graph_service.driver.session() as session:
        # Creăm o legătură între TOP SERVICES SRL (furnizorul nostru fictiv) și un angajat al firmei auditate
        session.run("""
            MERGE (f:Firma {valoare: 'TOP SERVICES SRL'})
            SET f.name = 'TOP SERVICES SRL'
            MERGE (p:Persoana {valoare: 'Popescu Ion'})
            SET p.name = 'Popescu Ion', p.functie = 'CONTABIL FIRMA AUDITATA'
            MERGE (f)-[:ASOCIAT_CU {tip: 'CONFLICT_INTERESE', risc: 'CRITIC'}]->(p)
        """)
        print("[+] Relație de conflict de interese (TOP SERVICES SRL <-> Popescu Ion) injectată în Neo4j.")

def generate_sample_audit_report(case_id: int):
    print(f"[*] Generare Raport de Audit pentru Case {case_id}...")
    db = ForensicSessionLocal()
    try:
        case = db.query(models.Case).filter(models.Case.id == case_id).first()
        if not case:
            print(f"[-] Case {case_id} nu a fost găsit.")
            return

        # Actualizăm scorul de risc automat în DB din cauza discrepanței
        case.risk_score = 98.5
        case.risk_explanation = "Discrepanță critică (138k RON) între facturi și balanță. Conflict de interese detectat în graf."
        db.commit()

        # Generăm PDF-ul
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt=f"RAPORT DE CONSTATARE FORENSIC - CASE #{case_id}", ln=True, align='C')
        pdf.set_font("Arial", size=12)
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Dosar: {case.name}", ln=True)
        pdf.cell(200, 10, txt=f"Data: 06.03.2026", ln=True)
        pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="CONSTATARI CRITICE:", ln=True)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 10, text="1. DISCREPANTA BALANTA (SEP 2018): Rulajul cumulat pe contul 704 raportat este de 111,969.58 RON. Totusi, facturile identificate (TS001, TS002) insumeaza 250,000.00 RON. Diferenta de 138,030.42 RON indica o posibila omisiune de inregistrare a veniturilor.")
        pdf.ln(2)
        pdf.multi_cell(0, 10, text="2. CONFLICT DE INTERESE: Furnizorul TOP SERVICES SRL este asociat direct cu Popescu Ion, care detine functia de Contabil in cadrul firmei auditate. Risc major de frauda interna.")
        
        pdf.ln(10)
        pdf.set_font("Helvetica", 'B', 14)
        pdf.set_text_color(200, 0, 0)
        pdf.cell(200, 10, text=f"SCOR DE RISC CALCULAT: {case.risk_score}%")
        
        report_path = f"/app/uploads/Raport_Constatare_Case_{case_id}.pdf"
        pdf.output(report_path)
        print(f"[+] Raport PDF salvat la: {report_path}")

    except Exception as e:
        print(f"[-] Eroare la generarea raportului: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    apply_db_upgrade()
    inject_graph_conflict()
    generate_sample_audit_report(2)
