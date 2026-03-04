from fastapi import FastAPI, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
import os
import hashlib
import shutil
from contextlib import asynccontextmanager

from .database import engine, SessionLocal, auth_engine, forensic_engine, AuthSessionLocal, ForensicSessionLocal, get_auth_db, get_forensic_db
from . import models
from .api import auth, cases, system
from .api.cases import get_current_user
from .core.audit import log_event

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Inițializăm Baza de Date FORENSIC
    try:
        from sqlalchemy import create_engine
        temp_eng = create_engine(os.getenv("FORENSIC_DATABASE_URL"))
        with temp_eng.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        temp_eng.dispose()
        models.ForensicBase.metadata.create_all(bind=forensic_engine)
        print("[+] Baza de date FORENSIC inițializată.")
    except Exception as e:
        print(f"[!] Eroare inițializare FORENSIC: {e}")

    # 2. Inițializăm Baza de Date AUTH
    try:
        models.AuthBase.metadata.create_all(bind=auth_engine)
        print("[+] Baza de date AUTH inițializată.")
    except Exception as e:
        print(f"[!] Eroare inițializare AUTH: {e}")
    
    # 3. Utilizatori Default
    db = AuthSessionLocal()
    try:
        from .core.security import get_password_hash
        if not db.query(models.User).filter(models.User.username == "admin").first():
            db.add(models.User(username="admin", hashed_password=get_password_hash("admin"), role="ADMIN", needs_password_change=1))
        if not db.query(models.User).filter(models.User.username == "master").first():
            db.add(models.User(username="master", hashed_password=get_password_hash("master"), role="MASTER", needs_password_change=1))
        db.commit()
    except Exception as e:
        print(f"[!] Eroare creare useri: {e}")
    finally:
        db.close()
    
    yield

app = FastAPI(
    title="Forensic DocAI V2",
    description="Arhitectură core_engine stabilă",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(system.router)

UPLOADS_DIR = "/app/uploads"
if not os.path.exists(UPLOADS_DIR): os.makedirs(UPLOADS_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

@app.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    case_id: int = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_forensic_db)
):
    for file in files:
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()
        await file.seek(0)
        
        existing = db.query(models.Document).filter(
            models.Document.case_id == case_id,
            models.Document.file_hash == file_hash
        ).first()
        
        if existing: continue

        file_path = os.path.join(UPLOADS_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        new_doc = models.Document(
            filename=file.filename,
            file_hash=file_hash,
            case_id=case_id,
            user_id=current_user.id,
            status="QUEUED"
        )
        db.add(new_doc)
        db.commit()
        log_event("DOCUMENT_UPLOADED", user_id=current_user.id, case_id=case_id, details={"filename": file.filename})
    
    return {"status": "queued"}

@app.get("/")
def health_check():
    return {"status": "operational", "engine": "core_engine"}
