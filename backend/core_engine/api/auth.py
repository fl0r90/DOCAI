from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from jose import jwt, JWTError
from ..database import get_auth_db, AuthSessionLocal, ForensicSessionLocal
from ..models import User
from ..core.security import verify_password, create_access_token, get_password_hash, SECRET_KEY, ALGORITHM
from ..core.audit import log_event

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# --------------------------------------------------------------------------- #
# Multi-Database User Synchronization Helpers
# --------------------------------------------------------------------------- #
def sync_users_auth_to_forensic():
    """Sincronizează toți utilizatorii din auth_db în forensic_db cu aceleași ID-uri."""
    auth_db = AuthSessionLocal()
    forensic_db = ForensicSessionLocal()
    try:
        auth_users = auth_db.query(User).all()
        for u in auth_users:
            f_user = forensic_db.query(User).filter(User.id == u.id).first()
            if not f_user:
                f_user = User(
                    id=u.id,
                    username=u.username,
                    hashed_password=u.hashed_password,
                    role=u.role,
                    is_active=getattr(u, "is_active", True),
                    needs_password_change=getattr(u, "needs_password_change", 0),
                    created_at=u.created_at
                )
                forensic_db.add(f_user)
            else:
                f_user.username = u.username
                f_user.hashed_password = u.hashed_password
                f_user.role = u.role
                f_user.is_active = getattr(u, "is_active", True)
                f_user.needs_password_change = getattr(u, "needs_password_change", 0)
        forensic_db.commit()
        forensic_db.execute(text("SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 1) FROM users))"))
        forensic_db.commit()
    except Exception as e:
        forensic_db.rollback()
        print(f"[!] Eroare sincronizare utilizatori în forensic_db: {e}")
    finally:
        auth_db.close()
        forensic_db.close()

def sync_single_user_to_forensic(user: User):
    """Sincronizează un utilizator individual în forensic_db."""
    forensic_db = ForensicSessionLocal()
    try:
        f_user = forensic_db.query(User).filter(User.id == user.id).first()
        if not f_user:
            f_user = User(
                id=user.id,
                username=user.username,
                hashed_password=user.hashed_password,
                role=user.role,
                is_active=getattr(user, "is_active", True),
                needs_password_change=getattr(user, "needs_password_change", 0),
                created_at=user.created_at
            )
            forensic_db.add(f_user)
        else:
            f_user.username = user.username
            f_user.hashed_password = user.hashed_password
            f_user.role = user.role
            f_user.is_active = getattr(user, "is_active", True)
            f_user.needs_password_change = getattr(user, "needs_password_change", 0)
        forensic_db.commit()
        forensic_db.execute(text("SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 1) FROM users))"))
        forensic_db.commit()
    except Exception as e:
        forensic_db.rollback()
        print(f"[!] Eroare sync single user in forensic_db: {e}")
    finally:
        forensic_db.close()

def remove_user_from_forensic(user_id: int):
    """Elimină un utilizator din forensic_db dacă există."""
    forensic_db = ForensicSessionLocal()
    try:
        f_user = forensic_db.query(User).filter(User.id == user_id).first()
        if f_user:
            forensic_db.delete(f_user)
            forensic_db.commit()
    except Exception as e:
        forensic_db.rollback()
        print(f"[!] Eroare ștergere user din forensic_db: {e}")
    finally:
        forensic_db.close()

# --------------------------------------------------------------------------- #
# Request Schemas
# --------------------------------------------------------------------------- #
class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

class ChangePasswordRequest(BaseModel):
    new_password: Optional[str] = None
    password: Optional[str] = None

class RequestResetRequest(BaseModel):
    username: str

class PriorityRequest(BaseModel):
    priority: int

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_auth_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None: raise credentials_exception
    return user

def check_admin_local(current_user: User = Depends(get_current_user)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Acces rezervat administratorilor.")
    return current_user

@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_auth_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or not verify_password(request.password, user.hashed_password):
        log_event("LOGIN_FAILED", details={"username": request.username}, severity="WARNING")
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    log_event("LOGIN_SUCCESS", user_id=user.id)
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "role": user.role,
        "needs_password_change": bool(user.needs_password_change)
    }

@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_auth_db)
):
    new_pwd = (request.new_password or request.password or "").strip()
    if not new_pwd or len(new_pwd) < 3:
        raise HTTPException(status_code=400, detail="Parola trebuie să conțină minim 3 caractere.")
    
    current_user.hashed_password = get_password_hash(new_pwd)
    current_user.needs_password_change = 0
    if hasattr(current_user, "reset_requested"):
        current_user.reset_requested = 0
    db.commit()
    db.refresh(current_user)

    sync_single_user_to_forensic(current_user)
    log_event("PASSWORD_CHANGED", user_id=current_user.id, details={"username": current_user.username})
    return {"status": "ok", "message": "Parola a fost actualizată cu succes."}

@router.post("/request-reset")
def request_reset(request: RequestResetRequest, db: Session = Depends(get_auth_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilizatorul nu a fost găsit.")
    if hasattr(user, "reset_requested"):
        user.reset_requested = 1
    db.commit()
    log_event("PASSWORD_RESET_REQUESTED", user_id=user.id, details={"username": user.username})
    return {"status": "ok", "message": "Cerere de resetare înregistrată cu succes."}

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "needs_password_change": bool(current_user.needs_password_change)
    }

@router.get("/users")
def get_users(admin: User = Depends(check_admin_local), db: Session = Depends(get_auth_db)):
    users = db.query(User).order_by(User.id.asc()).all()
    return [{
        "id": u.id, 
        "username": u.username, 
        "role": u.role, 
        "is_active": getattr(u, "is_active", True),
        "priority": getattr(u, "priority", 0) or 0,
        "needs_password_change": getattr(u, "needs_password_change", 0) or 0,
        "created_at": u.created_at
    } for u in users]

@router.post("/users")
def create_user(user_in: UserCreate, admin: User = Depends(check_admin_local), db: Session = Depends(get_auth_db)):
    existing = db.query(User).filter(User.username == user_in.username).first()
    if existing: raise HTTPException(status_code=400, detail="User already exists")
    new_user = User(
        username=user_in.username, 
        hashed_password=get_password_hash(user_in.password), 
        role=user_in.role, 
        needs_password_change=1
    )
    db.add(new_user); db.commit(); db.refresh(new_user)
    sync_single_user_to_forensic(new_user)
    log_event("USER_CREATED", user_id=admin.id, details={"new_user_id": new_user.id, "username": new_user.username, "role": new_user.role})
    return {"id": new_user.id, "username": new_user.username}

@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin: User = Depends(check_admin_local), db: Session = Depends(get_auth_db)):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Nu vă puteți șterge propriul cont.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilizatorul nu a fost găsit.")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="Contul de administrator principal nu poate fi șters.")
    username = user.username
    db.delete(user)
    db.commit()
    remove_user_from_forensic(user_id)
    log_event("USER_DELETED", user_id=admin.id, details={"deleted_user_id": user_id, "username": username})
    return {"status": "ok"}

@router.post("/users/{user_id}/priority")
def set_priority(user_id: int, req: PriorityRequest, admin: User = Depends(check_admin_local), db: Session = Depends(get_auth_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilizator inexistent.")
    user.priority = req.priority
    db.commit()
    return {"status": "ok", "priority": user.priority}
