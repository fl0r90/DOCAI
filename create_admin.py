from core_engine.database import SessionLocal
from core_engine.models import User
from core_engine.core.security import get_password_hash
import datetime
import os

# Ne asigurăm că folosim URL-ul corect pentru baza de date
# Poți seta variabila de mediu înainte de rulare sau va folosi default-ul de mai jos
db_url = os.getenv("AUTH_DATABASE_URL", "postgresql://forensic_admin:supersecret_dgx_password@localhost:5432/auth_db")

try:
    db = SessionLocal()
    # Curățăm orice intrare existentă pentru 'admin' ca să fim siguri
    db.query(User).filter(User.username == 'admin').delete()
    
    admin = User(
        username='admin',
        hashed_password=get_password_hash('admin'),
        role='ADMIN',
        created_at=datetime.datetime.now()
    )
    db.add(admin)
    db.commit()
    print('=========================================')
    print('SUCCES: Utilizator admin/admin a fost creat!')
    print('Baza de date: ' + db_url)
    print('=========================================')
except Exception as e:
    print('EROARE: ' + str(e))
finally:
    db.close()
