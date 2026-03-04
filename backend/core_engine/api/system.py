from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from ..database import get_db, get_auth_db, SessionLocal
from ..models import AuditLog, User, SystemSetting
from .. import models
from .auth import get_current_user
from sqlalchemy.orm import Session
from typing import Optional, List
import psutil
import docker
import os
import platform
import subprocess
import requests
import time
from pynvml import (
    nvmlInit, nvmlDeviceGetHandleByIndex, nvmlDeviceGetUtilizationRates, 
    nvmlDeviceGetTemperature, nvmlDeviceGetName, nvmlDeviceGetMemoryInfo, 
    nvmlShutdown, NVML_TEMPERATURE_GPU
)
from ..services.graph_service import graph_service

router = APIRouter(prefix="/system", tags=["system"])
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434")

def check_admin(user: User = Depends(get_current_user)):
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Acces rezervat administratorilor.")
    return user

def run_system_script(script_name: str, args: list = []):
    try:
        script_path = f"/app/{script_name}"
        if not os.path.exists(script_path): return f"Error: {script_name} not found"
        process = subprocess.Popen(["bash", script_path] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return stdout.decode() if stdout else stderr.decode()
    except Exception as e: return str(e)

@router.get("/metrics")
def get_metrics(admin: User = Depends(check_admin)):
    gpu_info = {"name": "N/A", "usage": 0, "temp": 0, "memory_total": 0, "memory_free": 0}
    try:
        nvmlInit()
        handle = nvmlDeviceGetHandleByIndex(0)
        mem = nvmlDeviceGetMemoryInfo(handle)
        gpu_info = {
            "name": nvmlDeviceGetName(handle),
            "usage": nvmlDeviceGetUtilizationRates(handle).gpu,
            "temp": nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU),
            "memory_total": round(mem.total / (1024**3), 1),
            "memory_free": round(mem.free / (1024**3), 1),
            "memory_used": round(mem.used / (1024**3), 1)
        }
        nvmlShutdown()
    except: pass
    
    cpu_temp = 0
    try:
        temps = psutil.sensors_temperatures()
        for name in ['coretemp', 'cpu_thermal', 'k10temp']:
            if name in temps: cpu_temp = temps[name][0].current; break
    except: pass

    usage = psutil.disk_usage('/')
    command = "cat /proc/cpuinfo | grep 'model name' | uniq | cut -d: -f2"
    cpu_name = subprocess.check_output(command, shell=True).decode().strip() if platform.system() == "Linux" else platform.processor()

    return {
        "cpu": {"name": cpu_name, "usage": psutil.cpu_percent(), "temp": round(cpu_temp, 1)},
        "ram": {"percent": psutil.virtual_memory().percent, "total": round(psutil.virtual_memory().total / (1024**3), 1), "free": round(psutil.virtual_memory().available / (1024**3), 1)},
        "gpu": gpu_info,
        "disk": {"percent": usage.percent, "total": round(usage.total / (1024**3), 1), "free": round(usage.free / (1024**3), 1)}
    }

@router.get("/docs/count")
def get_docs_count(admin: User = Depends(check_admin), db: Session = Depends(get_db)):
    return {"count": db.query(models.Document).count()}

@router.get("/models/active")
def get_active_model(db: Session = Depends(get_db)):
    setting = db.query(SystemSetting).filter(SystemSetting.key == "active_model").first()
    return {"active_model": setting.value if setting else "mistral-nemo:12b"}

@router.get("/models/available")
def get_available_models(admin: User = Depends(check_admin)):
    try:
        res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return res.json().get("models", []) if res.status_code == 200 else []
    except: return []

@router.get("/llm/config")
def get_llm_config_api(admin: User = Depends(check_admin), db: Session = Depends(get_db)):
    settings = db.query(SystemSetting).all()
    config = {s.key: s.value for s in settings}
    return {
        "active_model": config.get("active_model", "mistral-nemo:12b"),
        "chat_temp": float(config.get("chat_temp", 0.7)),
        "chat_ctx": int(config.get("chat_ctx", 16384)),
        
        "specialist_tabular": config.get("specialist_tabular", "qwen2.5-coder:7b"),
        "tabular_temp": float(config.get("tabular_temp", 0.0)),
        "tabular_ctx": int(config.get("tabular_ctx", 16384)),
        
        "specialist_narrative": config.get("specialist_narrative", "gemma2:27b"),
        "narrative_temp": float(config.get("narrative_temp", 0.1)),
        "narrative_ctx": int(config.get("narrative_ctx", 32768))
    }

@router.post("/llm/config")
def update_llm_config(payload: dict, admin: User = Depends(check_admin), db: Session = Depends(get_db)):
    for key, value in payload.items():
        s = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if s: s.value = str(value)
        else: db.add(SystemSetting(key=key, value=str(value)))
    db.commit()
    return {"message": "OK"}

@router.get("/audit")
def get_audit_logs(current_user: User = Depends(get_current_user), limit: int = 100, db: Session = Depends(get_db), auth_db: Session = Depends(get_auth_db)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    user_ids = list(set([l.user_id for l in logs if l.user_id]))
    users_map = {}
    if user_ids:
        users = auth_db.query(User).filter(User.id.in_(user_ids)).all()
        users_map = {u.id: u.username for u in users}
    return [{"id": l.id, "username": users_map.get(l.user_id, "System"), "action": l.action_type, "details": l.details, "created_at": l.created_at} for l in logs]

@router.get("/docker/containers")
def get_docker_containers(admin: User = Depends(check_admin)):
    try:
        client = docker.from_env()
        return [{"id": c.short_id, "name": c.name, "status": c.status, "image": c.image.tags[0] if c.image.tags else "unknown"} for c in client.containers.list()]
    except: return []

@router.get("/docker/logs/{container_name}")
def get_container_logs(container_name: str, admin: User = Depends(check_admin)):
    try:
        client = docker.from_env()
        return {"logs": client.containers.get(container_name).logs(tail=100).decode('utf-8')}
    except: return {"logs": "Error"}

@router.get("/updates/available")
def list_updates(admin: User = Depends(check_admin)):
    return [f for f in os.listdir("/app/updates") if f.endswith(('.sh', '.tar.gz'))] if os.path.exists("/app/updates") else []

@router.get("/backups/available")
def list_backups(admin: User = Depends(check_admin)):
    return [f for f in os.listdir("/app/backups/rollback") if f.endswith('.tar.gz')] if os.path.exists("/app/backups/rollback") else []

@router.post("/backup/trigger")
def trigger_backup(bg_tasks: BackgroundTasks, admin: User = Depends(check_admin)):
    ts = time.strftime("%Y%m%d_%H%M%S")
    bg_tasks.add_task(run_system_script, "pack_v2.sh", [ts])
    return {"message": f"Backup started: {ts}"}
