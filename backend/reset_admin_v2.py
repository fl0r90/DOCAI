from app.database import SessionLocal
from app.models import User
from app.core.security import get_password_hash

def reset():
    db = SessionLocal()
    user = db.query(User).filter(User.username == 'admin').first()
    if user:
        user.hashed_password = get_password_hash('admin123')
        user.needs_password_change = 0
        db.commit()
        print("Password reset to admin123 for user admin")
    else:
        print("User admin not found")
    db.close()

if __name__ == "__main__":
    reset()
