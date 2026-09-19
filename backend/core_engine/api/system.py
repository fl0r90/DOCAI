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
    gpu_info = {"name": "N/A", "usage": 0, "temp": 0, "memory_total": 0, "memory_free": 0, "memory_used": 0}
    
    # Încercăm întâi cu nvidia-smi (mai robust în Docker cu NVIDIA Runtime)
    try:
        cmd = "nvidia-smi --query-gpu=name,utilization.gpu,temperature.gpu,memory.total,memory.free,memory.used --format=csv,noheader,nounits"
        res = subprocess.check_output(cmd, shell=True).decode().strip().split(",")
        if len(res) >= 6:
            gpu_info = {
                "name": res[0].strip(),
                "usage": int(res[1].strip()),
                "temp": int(res[2].strip()),
                "memory_total": round(int(res[3].strip()) / 1024, 1),
                "memory_free": round(int(res[4].strip()) / 1024, 1),
                "memory_used": round(int(res[5].strip()) / 1024, 1)
            }
    except Exception as e:
        # Fallback la NVML dacă nvidia-smi eșuează
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
        except Exception as e2:
            print(f"[!] GPU Metrics Error (both methods): {e} | {e2}")
    
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

@router.get("/logs/live")
def get_live_logs(admin: User = Depends(check_admin)):
    try:
        client = docker.from_env()
        containers = {
            "v2-worker": "WORKER",
            "v2-backend": "BACKEND",
            "v2-llm-1": "LLM"
        }
        
        all_logs = []
        for c_name, label in containers.items():
            try:
                container = client.containers.get(c_name)
                # Preluăm ultimele 15 linii
                raw_logs = container.logs(tail=15).decode('utf-8', errors='ignore').split('\n')
                for line in raw_logs:
                    if line.strip():
                        # Filtrăm doar mesajele relevante de procesare
                        if any(x in line for x in ["[*]", "[+]", "[!]", "INFO", "ERROR", "Segment", "Docling"]):
                            all_logs.append({
                                "service": label,
                                "message": line.strip(),
                                "timestamp": time.time()
                            })
            except: continue
            
        # Returnăm logurile sortate aproximativ cronologic
        return sorted(all_logs, key=lambda x: x['timestamp'])[-30:]
    except Exception as e:
        return [{"service": "SYSTEM", "message": f"Eroare: {str(e)}"}]

@router.get("/docs/count")
def get_docs_count(admin: User = Depends(check_admin), db: Session = Depends(get_db)):
    return {"count": db.query(models.Document).count()}

@router.get("/models/active")
def get_active_model(db: Session = Depends(get_db)):
    setting = db.query(SystemSetting).filter(SystemSetting.key == "active_model").first()
    return {"active_model": setting.value if setting else "mistral-nemo:12b"}

@router.get("/models/available")
def get_available_models(admin: User = Depends(check_admin), db: Session = Depends(get_db)):
    settings = db.query(SystemSetting).all()
    config = {s.key: s.value for s in settings}
    engine = config.get("active_llm_engine", "ollama").lower()

    if engine == "lmstudio":
        lm_url = config.get("lmstudio_url") or os.getenv("LMSTUDIO_URL", "http://host.docker.internal:1234/v1")
        lm_url = lm_url.rstrip("/")
        if not lm_url.endswith("/v1"):
            lm_url = f"{lm_url}/v1"
        models_url = f"{lm_url}/models"
        headers = {}
        api_key = (config.get("lmstudio_api_key") or "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            res = requests.get(models_url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get("data") or data.get("models") or []
                result = []
                for item in items:
                    mid = item.get("id") or item.get("name") or item.get("model")
                    if mid:
                        result.append({
                            "name": mid,
                            "model": mid,
                            "details": {
                                "format": "gguf",
                                "family": item.get("owned_by") or "lmstudio",
                                "parameter_size": str(item.get("meta", {}).get("n_params", "N/A"))
                            }
                        })
                return result
            else:
                print(f"[!] LM Studio returned status {res.status_code}: {res.text}")
                return []
        except Exception as e:
            print(f"[!] Error fetching models from LM Studio ({models_url}): {e}")
            return []

    elif engine == "vllm":
        vllm_url = os.getenv("VLLM_URL", "http://vllm:8000/v1").rstrip("/")
        try:
            res = requests.get(f"{vllm_url}/models", timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get("data", [])
                return [{"name": m.get("id"), "model": m.get("id")} for m in items if m.get("id")]
            return []
        except Exception as e:
            print(f"[!] Error fetching models from vLLM: {e}")
            return []

    else:
        try:
            res = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            if res.status_code == 200:
                return res.json().get("models", [])
            else:
                print(f"[!] Ollama returned status {res.status_code}: {res.text}")
                return []
        except Exception as e:
            print(f"[!] Error fetching models from Ollama ({OLLAMA_URL}): {str(e)}")
            return []

@router.get("/llm/config")
def get_llm_config_api(admin: User = Depends(check_admin), db: Session = Depends(get_db)):
    settings = db.query(SystemSetting).all()
    config = {s.key: s.value for s in settings}
    active_model = config.get("active_model", "")
    processing_model = config.get("specialist_processing") or config.get("specialist_narrative") or config.get("specialist_tabular") or active_model
    return {
        "active_llm_engine": config.get("active_llm_engine", "ollama"),
        "active_model": active_model,
        "chat_temp": float(config.get("chat_temp", 0.7)),
        "chat_ctx": int(config.get("chat_ctx", 16384)),
        
        # Expert procesare unificat
        "specialist_processing": processing_model,
        "processing_temp": float(config.get("processing_temp", config.get("tabular_temp", 0.0))),
        "processing_ctx": int(config.get("processing_ctx", config.get("narrative_ctx", 32768))),

        # Retrocompatibilitate pentru UI-ul existent
        "specialist_tabular": processing_model,
        "tabular_temp": float(config.get("tabular_temp", 0.0)),
        "tabular_ctx": int(config.get("tabular_ctx", 16384)),
        
        "specialist_narrative": processing_model,
        "narrative_temp": float(config.get("narrative_temp", 0.1)),
        "narrative_ctx": int(config.get("narrative_ctx", 32768)),

        "lmstudio_url": config.get("lmstudio_url", os.getenv("LMSTUDIO_URL", "http://host.docker.internal:1234/v1")),
        "lmstudio_api_key": config.get("lmstudio_api_key", ""),
        "lmstudio_timeout": int(config.get("lmstudio_timeout", 300)),
        "ollama_api_mode": config.get("ollama_api_mode", os.getenv("OLLAMA_API_MODE", "native")),
        "reranker_device": config.get("reranker_device", os.getenv("RERANKER_DEVICE", "cpu")),
        "reranker_model": config.get("reranker_model", os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")),
    }

@router.post("/llm/config")
def update_llm_config(payload: dict, admin: User = Depends(check_admin), db: Session = Depends(get_db)):
    # Dacă specialist_processing este furnizat, sincronizăm automat și cheile vechi
    if "specialist_processing" in payload:
        payload["specialist_tabular"] = payload["specialist_processing"]
        payload["specialist_narrative"] = payload["specialist_processing"]
    elif "specialist_tabular" in payload and "specialist_processing" not in payload:
        payload["specialist_processing"] = payload["specialist_tabular"]
        payload["specialist_narrative"] = payload["specialist_tabular"]

    # Dacă LM Studio este activat, toți experții folosesc automat modelul unic încărcat
    if payload.get("active_llm_engine") == "lmstudio" and "active_model" in payload:
        payload["specialist_processing"] = payload["active_model"]
        payload["specialist_tabular"] = payload["active_model"]
        payload["specialist_narrative"] = payload["active_model"]

    for key, value in payload.items():
        s = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if s: s.value = str(value)
        else: db.add(SystemSetting(key=key, value=str(value)))
    db.commit()

    # Hot-reload RerankService dacă s-au schimbat parametrii de reranker
    if "reranker_device" in payload or "reranker_model" in payload:
        try:
            from ..services.rerank_service import RerankService
            RerankService.reset_instance()
        except Exception as e:
            print(f"[!] Warning la resetare RerankService: {e}")

    # LOGICA DE GESTIONARE CONTAINERE (Auto-Switch)
    if "active_llm_engine" in payload:
        engine = payload["active_llm_engine"]
        try:
            client = docker.from_env()
            if engine == "ollama":
                print("[*] Switch la Ollama: Oprim v2-vllm...")
                try: client.containers.get("v2-vllm").stop(timeout=5)
                except: pass
                print("[*] Pornim v2-llm-1...")
                try: client.containers.get("v2-llm-1").start()
                except: pass
            elif engine == "vllm":
                print("[*] Switch la vLLM: Oprim v2-llm-1...")
                try: client.containers.get("v2-llm-1").stop(timeout=5)
                except: pass
                print("[*] Pornim v2-vllm...")
                try: client.containers.get("v2-vllm").start()
                except: pass
            elif engine == "lmstudio":
                print("[*] Switch la LM Studio: Oprim v2-vllm dacă rula...")
                try: client.containers.get("v2-vllm").stop(timeout=5)
                except: pass
        except Exception as e:
            print(f"[!] Eroare gestionare containere la switch engine: {e}")

    return {"message": "OK"}

@router.post("/llm/test-connection")
def test_llm_connection(payload: dict, admin: User = Depends(check_admin)):
    """Testează conectivitatea cu un server LM Studio (local sau remote) sau OpenAI-compatible."""
    url = (payload.get("url") or "").strip().rstrip("/")
    api_key = (payload.get("api_key") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL-ul serverului este obligatoriu.")

    if url.endswith("/models"):
        models_url = url
    elif url.endswith("/v1"):
        models_url = f"{url}/models"
    else:
        models_url = f"{url}/v1/models"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    start_t = time.time()
    try:
        res = requests.get(models_url, headers=headers, timeout=5)
        latency_ms = round((time.time() - start_t) * 1000, 1)
        if res.status_code == 200:
            data = res.json()
            models_list = []
            if isinstance(data, dict):
                items = data.get("data") or data.get("models") or []
                for item in items:
                    mid = item.get("id") or item.get("name") or item.get("model")
                    if mid:
                        models_list.append(mid)
            return {
                "success": True,
                "latency_ms": latency_ms,
                "models": models_list,
                "count": len(models_list)
            }
        else:
            return {
                "success": False,
                "status_code": res.status_code,
                "error": f"Serverul a returnat HTTP {res.status_code}: {res.text[:200]}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Eroare de conexiune: {str(e)}"
        }

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

@router.post("/updates/apply/{filename}")
def apply_update(filename: str, bg_tasks: BackgroundTasks, admin: User = Depends(check_admin)):
    update_path = f"/app/updates/{filename}"
    if not os.path.exists(update_path):
        raise HTTPException(status_code=404, detail="Pachetul de update nu a fost găsit.")
    bg_tasks.add_task(run_system_script, "apply_update.sh", [update_path])
    return {"message": f"Aplicarea update-ului {filename} a fost inițiată în fundal."}

@router.get("/queue/status")
def queue_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Starea cozii de procesare a documentelor (pentru pagina principală)."""
    import redis as _redis
    queue_total = db.query(models.Document).filter(models.Document.status.in_(["QUEUED", "PROCESSING"])).count()
    processing = db.query(models.Document).filter(models.Document.status == "PROCESSING").count()
    is_llm_active = False
    try:
        _r = _redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        is_llm_active = bool(_r.exists("llm_active_session"))
    except Exception:
        pass
    return {
        "queue_total": queue_total,
        "position": processing or (1 if queue_total else 0),
        "eta_minutes": queue_total * 3,  # estimare grosieră: ~3 min/document
        "is_llm_active": is_llm_active,
    }

# --------------------------------------------------------------------------- #
# Graph analytics globale (toate dosarele) - folosite de dashboard/graph
# Schema de id-uri identică cu /cases/{id}/graph: case_/doc_/ent_
# --------------------------------------------------------------------------- #
def _build_global_graph(db: Session):
    from collections import defaultdict
    from sqlalchemy import text as _text
    nodes = {}
    adjacency = defaultdict(set)

    def add_link(a, b):
        adjacency[a].add(b)
        adjacency[b].add(a)

    for c in db.query(models.Case).all():
        nodes[f"case_{c.id}"] = {"id": f"case_{c.id}", "name": c.name, "label": "CASE"}
    for d in db.query(models.Document).all():
        nid = f"doc_{d.id}"
        nodes[nid] = {"id": nid, "name": d.filename, "filename": d.filename, "label": "DOC"}
        if d.case_id:
            add_link(f"case_{d.case_id}", nid)

    rows = db.execute(_text("""
        SELECT l.document_id, e.id, e.official_name
        FROM document_entity_links l JOIN master_entities e ON e.id = l.entity_id
    """)).fetchall()
    for doc_id, ent_id, name in rows:
        if not name:
            continue
        nid = f"ent_{ent_id}"
        if nid not in nodes:
            nodes[nid] = {"id": nid, "name": name, "label": "ENTITY"}
        add_link(f"doc_{doc_id}", nid)
    return nodes, adjacency

@router.get("/graph")
def get_global_graph(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returnează graful relațional global (toate dosarele, documentele și entitățile)."""
    nodes, adjacency = _build_global_graph(db)
    links = []
    seen = set()
    for src, targets in adjacency.items():
        for tgt in targets:
            pair = tuple(sorted([src, tgt]))
            if pair not in seen:
                seen.add(pair)
                links.append({"source": src, "target": tgt})
    return {"nodes": list(nodes.values()), "links": links}

@router.get("/graph/analytics/leader")
def global_leader(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _, adjacency = _build_global_graph(db)
    return {nid: len(neigh) for nid, neigh in adjacency.items()}

@router.get("/graph/analytics/cartel")
def global_cartel(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from collections import deque
    nodes, adjacency = _build_global_graph(db)
    community, cid = {}, 0
    for nid in nodes:
        if nid in community:
            continue
        community[nid] = cid
        q = deque([nid])
        while q:
            cur = q.popleft()
            for nb in adjacency.get(cur, []):
                if nb not in community:
                    community[nb] = cid; q.append(nb)
        cid += 1
    return community

@router.get("/graph/analytics/path")
def global_path(source_name: str, target_name: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from collections import deque
    nodes, adjacency = _build_global_graph(db)

    def find_id(name):
        name = name.strip().lower()
        for n in nodes.values():
            if name in str(n.get("name", "")).lower():
                return n["id"]
        return None

    src, dst = find_id(source_name), find_id(target_name)
    if not src or not dst:
        return {"nodes": []}
    prev = {src: None}
    q = deque([src])
    while q:
        cur = q.popleft()
        if cur == dst:
            break
        for nb in adjacency.get(cur, []):
            if nb not in prev:
                prev[nb] = cur; q.append(nb)
    if dst not in prev:
        return {"nodes": []}
    path, cur = [], dst
    while cur is not None:
        path.append(cur); cur = prev[cur]
    return {"nodes": list(reversed(path))}

@router.get("/graph/analytics/clones")
def global_clones(cui: str = "", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Entități suspecte: împart același CUI sau aceeași adresă (posibile firme-clonă)."""
    from sqlalchemy import text as _text
    clones = []
    # 1. Același CUI
    if cui:
        same = db.query(models.MasterEntity).filter(models.MasterEntity.cui_cif_cnp == cui).all()
        for i in range(len(same)):
            for j in range(i + 1, len(same)):
                clones.append({"suspect_id": f"ent_{same[i].id}", "clone_id": f"ent_{same[j].id}"})
    # 2. Aceeași adresă (non-goală)
    rows = db.execute(_text("""
        SELECT address, array_agg(id) AS ids FROM master_entities
        WHERE address IS NOT NULL AND address <> ''
        GROUP BY address HAVING COUNT(*) > 1
    """)).fetchall()
    for _addr, ids in rows:
        ids = list(ids)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                clones.append({"suspect_id": f"ent_{ids[i]}", "clone_id": f"ent_{ids[j]}"})
    return {"clones": clones}

@router.get("/backups/available")
def list_backups(admin: User = Depends(check_admin)):
    backup_path = "/app/backups/manual"
    if not os.path.exists(backup_path):
        os.makedirs(backup_path, exist_ok=True)
    return [f for f in os.listdir(backup_path) if f.startswith('DOCAI_BACKUP_') and f.endswith('.tar.gz')]

@router.post("/backup/trigger")
def trigger_backup(bg_tasks: BackgroundTasks, admin: User = Depends(check_admin)):
    # Rulăm scriptul de backup de date
    bg_tasks.add_task(run_system_script, "scripts/backup_v2.sh")
    return {"message": "Backup de date inițiat în fundal."}

@router.post("/backups/restore/{filename}")
def restore_backup(filename: str, bg_tasks: BackgroundTasks, admin: User = Depends(check_admin)):
    backup_path = f"/app/backups/manual/{filename}"
    if not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="Fișierul de backup nu a fost găsit.")
    
    # Rulăm restaurarea
    # Atenție: Această operațiune va restarta practic conexiunile la bazele de date
    bg_tasks.add_task(run_system_script, "scripts/restore_v2.sh", [backup_path])
    return {"message": "Restaurarea a fost inițiată. Sistemul ar putea fi indisponibil câteva momente."}

def _run_model_import_task(item_name: str):
    import redis, json, zipfile, tarfile, shutil, re
    r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
    import_dir = "/app/ollama_models/import"
    target_dir = "/app/ollama_models"
    item_path = os.path.join(import_dir, item_name)
    progress_key = "model_import_progress"

    r.set(progress_key, json.dumps({
        "active": True,
        "item": item_name,
        "status": "processing",
        "detail": f"Procesare '{item_name}'...",
        "percent": 10
    }), ex=3600)

    try:
        low = item_name.lower()
        imported_gguf_name = None

        # 1. Arhivă ZIP / TAR -> Dezarhivare automată
        if low.endswith(".zip") or low.endswith(".tar.gz") or low.endswith(".tgz") or low.endswith(".tar"):
            extract_tmp = os.path.join(import_dir, f"_extracted_{int(time.time())}")
            os.makedirs(extract_tmp, exist_ok=True)
            r.set(progress_key, json.dumps({
                "active": True,
                "item": item_name,
                "status": "unzipping",
                "detail": "Dezarhivare arhivă în curs...",
                "percent": 30
            }), ex=3600)

            if low.endswith(".zip"):
                with zipfile.ZipFile(item_path, 'r') as zf:
                    zf.extractall(extract_tmp)
            elif low.endswith(".tar.gz") or low.endswith(".tgz"):
                with tarfile.open(item_path, 'r:gz') as tf:
                    tf.extractall(extract_tmp)
            elif low.endswith(".tar"):
                with tarfile.open(item_path, 'r:') as tf:
                    tf.extractall(extract_tmp)

            # Căutăm fișiere .gguf extrase
            gguf_files = []
            for root, _, files in os.walk(extract_tmp):
                for f in files:
                    if f.lower().endswith(".gguf"):
                        gguf_files.append(os.path.join(root, f))

            if not gguf_files:
                raise ValueError("Arhiva nu conține niciun fișier .gguf!")

            src_gguf = gguf_files[0]
            dest_filename = os.path.basename(src_gguf)
            dest_path = os.path.join(target_dir, dest_filename)
            shutil.move(src_gguf, dest_path)
            shutil.rmtree(extract_tmp, ignore_errors=True)
            try:
                os.remove(item_path)
            except Exception:
                pass
            imported_gguf_name = dest_filename

        # 2. Fișier GGUF direct
        elif low.endswith(".gguf"):
            dest_path = os.path.join(target_dir, item_name)
            shutil.move(item_path, dest_path)
            imported_gguf_name = item_name

        # 3. Subfolder (Structură Ollama blobs/manifests sau folder cu .gguf)
        elif os.path.isdir(item_path):
            if os.path.exists(os.path.join(item_path, "blobs")) or os.path.exists(os.path.join(item_path, "manifests")):
                for it in os.listdir(item_path):
                    s = os.path.join(item_path, it)
                    d = os.path.join(target_dir, it)
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
                shutil.rmtree(item_path, ignore_errors=True)
                r.set(progress_key, json.dumps({
                    "active": False,
                    "item": item_name,
                    "status": "completed",
                    "detail": "Structura Ollama a fost importată cu succes!",
                    "percent": 100
                }), ex=3600)
                return
            else:
                found_ggufs = [f for f in os.listdir(item_path) if f.lower().endswith(".gguf")]
                if not found_ggufs:
                    raise ValueError("Folderul nu conține niciun fișier .gguf!")
                dest_filename = found_ggufs[0]
                shutil.move(os.path.join(item_path, dest_filename), os.path.join(target_dir, dest_filename))
                shutil.rmtree(item_path, ignore_errors=True)
                imported_gguf_name = dest_filename
        else:
            raise ValueError(f"Format nesuportat pentru {item_name}")

        # Înregistrare automată în Ollama prin REST API nativ
        clean_tag = re.sub(r'\.gguf$', '', imported_gguf_name, flags=re.IGNORECASE)
        clean_tag = re.sub(r'[^a-zA-Z0-9_.-]', '-', clean_tag).lower().strip("-")
        if ":" not in clean_tag:
            clean_tag = f"{clean_tag}:latest"

        r.set(progress_key, json.dumps({
            "active": True,
            "item": item_name,
            "status": "registering",
            "detail": f"Înregistrare în Ollama sub tag-ul '{clean_tag}'...",
            "percent": 70
        }), ex=3600)

        ollama_payload = {
            "name": clean_tag,
            "from": f"/root/.ollama/{imported_gguf_name}"
        }
        res = requests.post(f"{OLLAMA_URL}/api/create", json=ollama_payload, timeout=600)
        if res.status_code == 200:
            r.set(progress_key, json.dumps({
                "active": False,
                "item": item_name,
                "status": "completed",
                "detail": f"Modelul '{clean_tag}' a fost înregistrat cu succes în Ollama!",
                "percent": 100,
                "model_name": clean_tag
            }), ex=3600)
        else:
            raise RuntimeError(f"Ollama a returnat eroarea {res.status_code}: {res.text}")

    except Exception as e:
        print(f"[!] Eroare la import model {item_name}: {e}")
        r.set(progress_key, json.dumps({
            "active": False,
            "item": item_name,
            "status": "error",
            "detail": str(e),
            "percent": 0
        }), ex=3600)


@router.get("/models/import/available")
def list_import_models(admin: User = Depends(check_admin)):
    import_path = "/app/ollama_models/import"
    if not os.path.exists(import_path):
        os.makedirs(import_path, exist_ok=True)
    items = []
    try:
        for entry in os.listdir(import_path):
            if entry.startswith(".") or entry.startswith("_"):
                continue
            full_p = os.path.join(import_path, entry)
            if os.path.isdir(full_p):
                size_mb = 0
                try:
                    size_mb = round(sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fn in os.walk(full_p) for f in fn) / (1024 * 1024), 1)
                except Exception: pass
                items.append({
                    "name": entry,
                    "type": "folder",
                    "size_mb": size_mb,
                    "display": f"{entry} (Folder - {size_mb} MB)"
                })
            elif os.path.isfile(full_p):
                size_mb = round(os.path.getsize(full_p) / (1024 * 1024), 1)
                low = entry.lower()
                if low.endswith(".gguf"):
                    items.append({
                        "name": entry,
                        "type": "gguf",
                        "size_mb": size_mb,
                        "display": f"{entry} (Model GGUF - {size_mb} MB)"
                    })
                elif low.endswith(".zip") or low.endswith(".tar.gz") or low.endswith(".tgz") or low.endswith(".tar"):
                    items.append({
                        "name": entry,
                        "type": "archive",
                        "size_mb": size_mb,
                        "display": f"{entry} (Arhivă - {size_mb} MB)"
                    })
    except Exception as e:
        print(f"[!] Eroare listare import modele: {e}")
    return items

@router.post("/models/import/run/{item_name}")
def run_model_import(item_name: str, bg_tasks: BackgroundTasks, admin: User = Depends(check_admin)):
    import_path = f"/app/ollama_models/import/{item_name}"
    if not os.path.exists(import_path):
        raise HTTPException(status_code=404, detail="Elementul specificat nu a fost găsit în import/.")
    bg_tasks.add_task(_run_model_import_task, item_name)
    return {"message": f"Importul pentru '{item_name}' a fost inițiat în fundal."}

@router.get("/models/import/status")
def get_import_status(admin: User = Depends(check_admin)):
    import redis, json
    r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
    raw = r.get("model_import_progress")
    if raw:
        try:
            return json.loads(raw.decode('utf-8') if isinstance(raw, bytes) else raw)
        except Exception: pass
    return {"active": False, "status": "idle"}

def _pull_model_worker(model_name: str):
    import redis, json
    r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
    progress_key = "model_pull_progress"
    r.set(progress_key, json.dumps({
        "active": True,
        "model": model_name,
        "status": "connecting",
        "detail": f"Conectare la registru pentru '{model_name}'...",
        "percent": 0
    }), ex=7200)

    try:
        res = requests.post(f"{OLLAMA_URL}/api/pull", json={"name": model_name, "stream": True}, stream=True, timeout=7200)
        if res.status_code != 200:
            raise RuntimeError(f"Ollama a returnat status {res.status_code}: {res.text}")

        for line in res.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    status_str = data.get("status", "")
                    total = data.get("total", 0)
                    completed = data.get("completed", 0)
                    pct = round((completed / total) * 100, 1) if total > 0 else 0

                    r.set(progress_key, json.dumps({
                        "active": True,
                        "model": model_name,
                        "status": "downloading",
                        "detail": f"{status_str} ({pct}%)" if pct > 0 else status_str or "Descărcare...",
                        "percent": pct
                    }), ex=7200)

                    if status_str == "success":
                        r.set(progress_key, json.dumps({
                            "active": False,
                            "model": model_name,
                            "status": "completed",
                            "detail": f"Modelul '{model_name}' a fost descărcat cu succes!",
                            "percent": 100
                        }), ex=7200)
                        return
                except Exception: pass

        r.set(progress_key, json.dumps({
            "active": False,
            "model": model_name,
            "status": "completed",
            "detail": f"Descărcare finalizată pentru '{model_name}'!",
            "percent": 100
        }), ex=7200)
    except Exception as e:
        print(f"[!] Eroare la pull model {model_name}: {e}")
        r.set(progress_key, json.dumps({
            "active": False,
            "model": model_name,
            "status": "error",
            "detail": str(e),
            "percent": 0
        }), ex=7200)

@router.post("/models/pull")
def pull_model(payload: dict, bg_tasks: BackgroundTasks, admin: User = Depends(check_admin)):
    model_name = (payload.get("name") or "").strip()
    if not model_name:
        raise HTTPException(status_code=400, detail="Specificați numele sau tag-ul modelului.")
    bg_tasks.add_task(_pull_model_worker, model_name)
    return {"message": f"Descărcarea modelului '{model_name}' a fost inițiată în fundal."}

@router.get("/models/pull/status")
def get_pull_status(admin: User = Depends(check_admin)):
    import redis, json
    r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
    raw = r.get("model_pull_progress")
    if raw:
        try:
            return json.loads(raw.decode('utf-8') if isinstance(raw, bytes) else raw)
        except Exception: pass
    return {"active": False, "status": "idle"}

@router.post("/models/delete")
def delete_ollama_model(model_name: str, admin: User = Depends(check_admin)):
    try:
        print(f"[*] Cerere stergere model (via POST): {model_name}")
        # Apelăm API-ul Ollama pentru a șterge modelul de pe disc
        res = requests.delete(f"{OLLAMA_URL}/api/delete", json={"name": model_name}, timeout=30)
        if res.status_code == 200:
            print(f"[+] Model {model_name} sters cu succes.")
            return {"message": f"Modelul {model_name} a fost șters."}
        else:
            print(f"[!] Ollama a returnat {res.status_code} la stergere.")
            return {"message": f"Ollama return: {res.status_code}"}
    except Exception as e:
        print(f"[-] Eroare stergere model {model_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workers")
def list_active_workers(admin: User = Depends(check_admin)):
    """Monitorizează nodurile de procesare active (locale sau remote) via Redis heartbeats."""
    import redis, json
    r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
    now = int(time.time())
    keys = r.keys("worker_heartbeat_*")
    workers = []
    for k in keys:
        try:
            raw = r.get(k)
            if raw:
                val = json.loads(raw.decode('utf-8') if isinstance(raw, bytes) else raw)
                diff = now - val.get("timestamp", now)
                workers.append({
                    "worker_id": val.get("worker_id"),
                    "status": val.get("status", "UNKNOWN"),
                    "current_doc": val.get("current_doc"),
                    "last_seen_seconds_ago": diff,
                    "alive": diff < 65
                })
        except Exception:
            continue
    return {"active_workers": workers, "count": len(workers)}


@router.get("/debug-logs")
def get_debug_logs(
    limit: int = 100,
    offset: int = 0,
    level: Optional[str] = None,
    service: Optional[str] = None,
    admin: User = Depends(check_admin)
):
    """
    Servește în timp real logurile structurate de telemetrie criminalistică (JSONL).
    Folosește căutare binară inversă (tail) pentru acces sub-milisecundă cu zero overhead RAM.
    """
    from ..services.debug_logger import debug_logger
    safe_limit = min(max(1, limit), 500)
    return debug_logger.get_recent_logs(limit=safe_limit, offset=offset, level=level, service=service)
