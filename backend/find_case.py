import sys
sys.path.append('/app')
from core_engine.database import SessionLocal
from core_engine.models import Document, Case
from sqlalchemy import func

with SessionLocal() as db:
    cases = db.query(Case.id, Case.name, func.count(Document.id)).outerjoin(Document).group_by(Case.id).all()
    for c in cases:
        print(f"Case {c[0]}: {c[1]} - {c[2]} documents")
