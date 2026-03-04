from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from jose import jwt, JWTError
from ..database import get_auth_db
from ..models import User
from ..core.security import verify_password, create_access_token, get_password_hash, SECRET_KEY, ALGORITHM
from ..core.audit import log_event

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

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
    users = db.query(User).all()
    return [{"id": u.id, "username": u.username, "role": u.role, "created_at": u.created_at} for u in users]

@router.post("/users")
def create_user(user_in: UserCreate, admin: User = Depends(check_admin_local), db: Session = Depends(get_auth_db)):
    existing = db.query(User).filter(User.username == user_in.username).first()
    if existing: raise HTTPException(status_code=400, detail="User already exists")
    new_user = User(username=user_in.username, hashed_password=get_password_hash(user_in.password), role=user_in.role, needs_password_change=1)
    db.add(new_user); db.commit(); db.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username}
