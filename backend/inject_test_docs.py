import os
import hashlib
from core_engine.database import ForensicSessionLocal
from core_engine.models import Document

CASE_ID = 5
UPLOADS_DIR = '/app/uploads'
USER_ID = 1

db = ForensicSessionLocal()
try:
    for filename in os.listdir(UPLOADS_DIR):
        if not filename.startswith('0') and not filename.startswith('10'): continue
        if not filename.endswith('.pdf'): continue
        
        file_path = os.path.join(UPLOADS_DIR, filename)
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
            
        existing = db.query(Document).filter(Document.file_hash == file_hash).first()
        if existing:
            print(f'Skipping {filename} - already exists.')
            continue
            
        new_doc = Document(
            filename=filename,
            file_hash=file_hash,
            case_id=CASE_ID,
            user_id=USER_ID,
            status='QUEUED'
        )
        db.add(new_doc)
        print(f'Added {filename} to QUEUE.')
    db.commit()
except Exception as e:
    print(f'Error: {e}')
finally:
    db.close()
