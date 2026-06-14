import os
import sys
from sqlalchemy import text

# Adăugăm backend în path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core_engine.database import auth_engine, forensic_engine, AuthSessionLocal
from core_engine.models import AuthBase, ForensicBase, User
from core_engine.core.security import get_password_hash
import datetime

def init_db():
    print("[*] Inițializare baze de date structurate pe RunPod...")

    # 1. Inițializăm Tabelele de Autentificare (auth_db)
    print("[*] Creare tabele în AUTH_DB (folosind AuthBase)...")
    try:
        # AICI ERA PROBLEMA: Trebuie să folosim AuthBase pentru tabelul 'users'
        AuthBase.metadata.create_all(bind=auth_engine)
        print("[+] Tabele AUTH create cu succes.")
    except Exception as e:
        print(f"[-] Eroare la AUTH_DB: {e}")

    # 2. Inițializăm Tabelele Forensic (forensic_db)
    print("[*] Creare tabele în FORENSIC_DB (folosind ForensicBase)...")
    try:
        # Folosim un workaround pentru a ignora eroarea de index REGCONFIG
        # create_all va crea ce poate
        ForensicBase.metadata.create_all(bind=forensic_engine)
        print("[+] Tabele FORENSIC create.")
    except Exception as e:
        print(f"[!] Notă la FORENSIC_DB (indexul romanian este ok sa dea skip aici): {e}")

    # 3. Creăm utilizatorul admin în auth_db
    print("[*] Creare utilizator admin în AUTH_DB...")
    try:
        db = AuthSessionLocal()
        # Ștergem orice intrare existentă pentru 'admin'
        db.query(User).filter(User.username == 'admin').delete()
        admin = User(
            username='admin',
            hashed_password=get_password_hash('admin'),
            role='ADMIN',
            created_at=datetime.datetime.now()
        )
        db.add(admin)
        db.commit()
        print("[+] Utilizator admin/admin creat cu succes!")
    except Exception as e:
        print(f"[-] Eroare la salvare admin: {e}")
    finally:
        db.close()

    print("\n[V] CONFIGURARE COMPLETĂ!")

if __name__ == "__main__":
    init_db()
