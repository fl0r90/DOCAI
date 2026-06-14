import os
import subprocess
import sys

# Importuri pentru baza de date
try:
    # Adaugam /app in path pentru a vedea core_engine
    sys.path.append("/app")
    from core_engine.database import SessionLocal
    from core_engine.models import SystemSetting
except ImportError as e:
    print(f"[!] Modulele core_engine nu sunt disponibile: {e}")
    SessionLocal = None

def get_db_config():
    """Citește configurația din baza de date."""
    if not SessionLocal:
        return {}
    db = SessionLocal()
    try:
        settings = db.query(SystemSetting).all()
        config = {s.key: s.value for s in settings}
        return config
    except Exception as e:
        print(f"[!] Eroare citire DB: {e}")
        return {}
    finally:
        db.close()

if __name__ == "__main__":
    db_config = get_db_config()
    
    # Parametri din DB sau Default
    model = db_config.get("active_model", "casperhansen/deepseek-r1-distill-qwen-14b-awq")
    
    # Daca modelul nu incepe cu / si nu e un URL, incercam sa-l localizam in cache-ul local
    if not model.startswith("/") and not model.startswith("http"):
        local_path = f"/root/.cache/huggingface/{model}"
        if os.path.exists(local_path):
            model = local_path
            print(f"[*] Mapare model la cale locala: {model}")

    kv_dtype = db_config.get("vllm_kv_cache_dtype", "fp8_e4m3")
    gpu_util = db_config.get("vllm_gpu_utilization", "0.70")
    max_len = db_config.get("chat_ctx", "8192")

    print(f"[*] WRAPPER: Pornire vLLM cu Model={model}, KV={kv_dtype}, GPU={gpu_util}, Ctx={max_len}")

    # Construim comanda de lansare oficiala vLLM
    cmd = [
        "python3", "-m", "vllm.entrypoints.openai.api_server",
        "--model", model,
        "--kv-cache-dtype", kv_dtype,
        "--gpu-memory-utilization", gpu_util,
        "--max-model-len", max_len,
        "--trust-remote-code",
        "--disable-log-stats",
        "--host", "0.0.0.0",
        "--port", "8000"
    ]

    # Executam vLLM (inlocuim procesul curent)
    os.execvp(cmd[0], cmd)
