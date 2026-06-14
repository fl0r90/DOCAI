
import sys
import os
import time
from sqlalchemy import text
sys.path.append("/home/cfp-90/AI/V2/backend")

from core_engine.database import ForensicSessionLocal
from core_engine.models import Document, DocumentChunk

def check():
    db = ForensicSessionLocal()
    doc = db.query(Document).filter(Document.id == 14).first()
    print(f"Status document: {doc.status}")
    
    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == 14).limit(5).all()
    for c in chunks:
        print(f"Chunk ID {c.id}, Page {c.page_number}, Spatial: {c.spatial}")
    
    db.close()

if __name__ == "__main__":
    check()
