import sys
import os
sys.path.append('/home/cfp-90/AI/V2/backend')
from app.database import SessionLocal
from app import models
from app.core.security import get_password_hash

def reset_admin():
    db = SessionLocal()
    admin = db.query(models.User).filter(models.User.username == "admin").first()
    if admin:
        admin.hashed_password = get_password_hash("admin123")
        admin.needs_password_change = 0
        db.commit()
        print("[!] Parola pentru 'admin' a fost resetata la: admin123")
    else:
        print("[-] Utilizatorul admin nu a fost gasit.")
    db.close()

if __name__ == "__main__":
    reset_admin()
