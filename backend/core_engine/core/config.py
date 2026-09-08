import os
from ..database import SessionLocal
from ..models import SystemSetting

def get_llm_config():
    """Citește configurația LLM granulară din baza de date."""
    db = SessionLocal()
    try:
        settings = db.query(SystemSetting).all()
        config = {s.key: s.value for s in settings}
        return {
            "active_llm_engine": config.get("active_llm_engine", "vllm"),
            "active_model": config.get("active_model", "qwen3.5:9b"),
            "chat_temp": float(config.get("chat_temp", 0.7)),
            "chat_ctx": int(config.get("chat_ctx", 16384)),
            "safety_limit": int(config.get("safety_limit", 20000)),

            "specialist_tabular": config.get("specialist_tabular", "qwen2.5-coder:7b"),

            "tabular_temp": float(config.get("tabular_temp", 0.0)),
            "tabular_ctx": int(config.get("tabular_ctx", 16384)),
            
            "specialist_narrative": config.get("specialist_narrative", "gemma3:27b"),
            "narrative_temp": float(config.get("narrative_temp", 0.1)),
            "narrative_ctx": int(config.get("narrative_ctx", 32768)),

            # vLLM TurboQuant Settings
            "vllm_kv_cache_dtype": config.get("vllm_kv_cache_dtype", "turboquant"),
            "vllm_gpu_utilization": float(config.get("vllm_gpu_utilization", 0.90)),
            "vllm_max_model_len": int(config.get("vllm_max_model_len", 32768)),

            # LM Studio Settings (Local / Remote)
            "lmstudio_url": config.get("lmstudio_url", os.getenv("LMSTUDIO_URL", "http://host.docker.internal:1234/v1")),
            "lmstudio_api_key": config.get("lmstudio_api_key", ""),
            "lmstudio_timeout": int(config.get("lmstudio_timeout", 300))
        }
    except:
        return {
            "active_llm_engine": "ollama",
            "active_model": "phi4:latest", "chat_temp": 0.7, "chat_ctx": 16384,
            "specialist_tabular": "qwen2.5-coder:7b", "tabular_temp": 0.0, "tabular_ctx": 16384,
            "specialist_narrative": "gemma3:27b", "narrative_temp": 0.1, "narrative_ctx": 32768,
            "vllm_kv_cache_dtype": "turboquant", "vllm_gpu_utilization": 0.90, "vllm_max_model_len": 32768,
            "lmstudio_url": os.getenv("LMSTUDIO_URL", "http://host.docker.internal:1234/v1"),
            "lmstudio_api_key": "",
            "lmstudio_timeout": 300
        }
    finally:
        db.close()

def get_active_model_name():
    return get_llm_config()["active_model"]
