from core_engine.database import SessionLocal
from core_engine.models import User
from core_engine.core.security import get_password_hash
import datetime

try:
    db = SessionLocal()
    # Ștergem dacă există deja pentru a asigura un reset curat
    db.query(User).filter(User.username == 'admin').delete()
    
    admin = User(
        username='admin',
        hashed_password=get_password_hash('admin'),
        role='ADMIN',
        created_at=datetime.datetime.now()
    )
    db.add(admin)
    db.commit()
    print('GATA! Utilizator admin/admin creat cu succes.')
except Exception as e:
    print(f'Eroare: {e}')
finally:
    db.close()
