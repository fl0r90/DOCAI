from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

AUTH_URL = os.getenv("AUTH_DATABASE_URL", "postgresql://forensic_admin:supersecret_dgx_password@db:5432/auth_db")
FORENSIC_URL = os.getenv("FORENSIC_DATABASE_URL", "postgresql://forensic_admin:supersecret_dgx_password@db:5432/forensic_db")

# Motoarele pentru cele două baze separate
auth_engine = create_engine(AUTH_URL)
forensic_engine = create_engine(FORENSIC_URL)

# Sesiuni separate
AuthSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=auth_engine)
ForensicSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=forensic_engine)

# Aliasuri pentru compatibilitate inversă
SessionLocal = ForensicSessionLocal
engine = forensic_engine

Base = declarative_base()

# Dependințe pentru FastAPI
def get_auth_db():
    db = AuthSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_forensic_db():
    db = ForensicSessionLocal()
    try:
        yield db
    finally:
        db.close()

# get_db va returna baza de date operativă (Forensic)
get_db = get_forensic_db
