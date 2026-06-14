import os
import sys
sys.path.append('/app')
from core_engine.database import ForensicSessionLocal
from core_engine.models import Case
from fpdf import FPDF

def test_gen(case_id):
    db = ForensicSessionLocal()
    try:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            print(f"ERROR: Case {case_id} not found")
            return
        
        print(f"Testing Case {case_id}: {case.name}")
        print(f"Documents found: {len(case.documents)}")
        for d in case.documents:
            print(f" - {d.filename}: {d.status}")

        report_path = f"/app/uploads/test_report_{case_id}.pdf"
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, txt=f"TEST REPORT #{case_id}", ln=True)
        
        for doc in case.documents:
            pdf.set_font("Helvetica", size=10)
            pdf.cell(0, 10, txt=f"Doc: {doc.filename} ({doc.status})", ln=True)
        
        pdf.output(report_path)
        print(f"SUCCESS: Report saved to {report_path}")
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    test_gen(5)
