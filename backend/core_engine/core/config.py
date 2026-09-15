import os
from ..database import SessionLocal
from ..models import SystemSetting

def get_llm_config():
    """Citește configurația LLM granulară din baza de date fără modele hardcodate."""
    db = SessionLocal()
    try:
        settings = db.query(SystemSetting).all()
        config = {s.key: s.value for s in settings}
        active_model = config.get("active_model", "")
        # Expert procesare unificat: folosește specialist_processing dacă e setat, altfel active_model
        processing_model = config.get("specialist_processing") or config.get("specialist_narrative") or config.get("specialist_tabular") or active_model

        return {
            "active_llm_engine": config.get("active_llm_engine", "ollama"),
            "active_model": active_model,
            "chat_temp": float(config.get("chat_temp", 0.7)),
            "chat_ctx": int(config.get("chat_ctx", 16384)),
            "safety_limit": int(config.get("safety_limit", 20000)),

            # Expert procesare unic (pentru ingestie, OCR overview, tabele, sinteză și TOC)
            "specialist_processing": processing_model,
            "processing_temp": float(config.get("processing_temp", config.get("tabular_temp", 0.0))),
            "processing_ctx": int(config.get("processing_ctx", config.get("narrative_ctx", 32768))),

            # Retrocompatibilitate pentru codul care încă interoghează cheile vechi
            "specialist_tabular": processing_model,
            "tabular_temp": float(config.get("tabular_temp", 0.0)),
            "tabular_ctx": int(config.get("tabular_ctx", 16384)),
            
            "specialist_narrative": processing_model,
            "narrative_temp": float(config.get("narrative_temp", 0.1)),
            "narrative_ctx": int(config.get("narrative_ctx", 32768)),

            # vLLM Settings
            "vllm_kv_cache_dtype": config.get("vllm_kv_cache_dtype", "turboquant"),
            "vllm_gpu_utilization": float(config.get("vllm_gpu_utilization", 0.90)),
            "vllm_max_model_len": int(config.get("vllm_max_model_len", 32768)),

            # LM Studio Settings (Local / Remote)
            "lmstudio_url": config.get("lmstudio_url", os.getenv("LMSTUDIO_URL", "http://host.docker.internal:1234/v1")),
            "lmstudio_api_key": config.get("lmstudio_api_key", ""),
            "lmstudio_timeout": int(config.get("lmstudio_timeout", 300)),

            # Ollama API mode: "native" (/api/chat) | "openai" (/v1/chat/completions)
            "ollama_api_mode": config.get("ollama_api_mode", os.getenv("OLLAMA_API_MODE", "native")),
        }
    except:
        env_model = os.getenv("ACTIVE_MODEL", "")
        return {
            "active_llm_engine": os.getenv("ACTIVE_LLM_ENGINE", "ollama"),
            "active_model": env_model,
            "chat_temp": 0.7,
            "chat_ctx": 16384,
            "specialist_processing": os.getenv("SPECIALIST_PROCESSING", env_model),
            "processing_temp": 0.0,
            "processing_ctx": 32768,
            "specialist_tabular": os.getenv("SPECIALIST_PROCESSING", env_model),
            "tabular_temp": 0.0,
            "tabular_ctx": 16384,
            "specialist_narrative": os.getenv("SPECIALIST_PROCESSING", env_model),
            "narrative_temp": 0.1,
            "narrative_ctx": 32768,
            "vllm_kv_cache_dtype": "turboquant",
            "vllm_gpu_utilization": 0.90,
            "vllm_max_model_len": 32768,
            "lmstudio_url": os.getenv("LMSTUDIO_URL", "http://host.docker.internal:1234/v1"),
            "lmstudio_api_key": "",
            "lmstudio_timeout": 300,
            "ollama_api_mode": os.getenv("OLLAMA_API_MODE", "native"),
        }
    finally:
        db.close()

def get_active_model_name():
    return get_llm_config()["active_model"]
