import re
import os
import json
from sqlalchemy import create_engine, or_, and_
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, Text, Float, JSON, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer)
    filename = Column(Text)
    status = Column(Text)

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    page_number = Column(Integer)
    content = Column(Text)

FORENSIC_URL = os.getenv("FORENSIC_DATABASE_URL", "postgresql://forensic_admin:supersecret_dgx_password@db:5432/forensic_db")
engine = create_engine(FORENSIC_URL)
SessionLocal = sessionmaker(bind=engine)

def test_gather_evidence(case_id, user_question):
    print(f"Testing with Question: {user_question}")
    with SessionLocal() as db:
        doc_ids = [d.id for d in db.query(Document).filter(Document.case_id == case_id).all()]
        if not doc_ids: 
            print("No documents found for case")
            return

        anchors = re.findall(r'[A-Z]{3,30}|\d+[\.,]\d{2}|\d{4,}', user_question)
        print(f"Anchors found: {anchors}")
        
        all_chunks = []
        financial_evidence = ""
        
        if anchors:
            cond = and_(DocumentChunk.document_id.in_(doc_ids), or_(*[DocumentChunk.content.ilike(f"%{a}%") for a in anchors]))
            all_chunks = db.query(DocumentChunk).filter(cond).limit(15).all()
            print(f"Chunks found by anchors: {len(all_chunks)}")

        if not all_chunks:
            words = [w for w in re.findall(r'\w+', user_question.lower()) if len(w) >= 4]
            print(f"Words: {words}")
            if words:
                all_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(doc_ids), or_(*[DocumentChunk.content.ilike(f"%{w[:4]}%") for w in words])).limit(10).all()
            print(f"Chunks found by words: {len(all_chunks)}")

        injected_evidence = ""
        if all_chunks:
            injected_evidence = "--- AUTO-IDENTIFIED EVIDENCE --- \n"
            seen_ids = set()
            for r in all_chunks:
                if r.id in seen_ids: continue
                seen_ids.add(r.id)
                neighbors = db.query(DocumentChunk).filter(DocumentChunk.document_id == r.document_id, DocumentChunk.id >= r.id - 1, DocumentChunk.id <= r.id + 1).order_by(DocumentChunk.id).all()
                context = "\n".join([re.sub(r'> \[CONTEXT:.*?\]|> \[SPAȚIAL:.*?\]|={5,}', '', n.content).strip() for n in neighbors])
                injected_evidence += f"[Source {r.document_id}, Page {r.page_number}]:\n{context}\n---\n"
        
        print("Injected Evidence (First 200 chars):")
        print(injected_evidence[:200])
        return injected_evidence

if __name__ == "__main__":
    q = "Identifică tranzacțiile către ACVILE TECH din februarie 2026. Compară extrasul de cont cu factura acestora și calculează suma totală. Există vreo discrepanță între factură și plata reală?"
    test_gather_evidence(5, q)
