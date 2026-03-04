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
    except:
        return {
            "active_model": "mistral-nemo:12b", "chat_temp": 0.7, "chat_ctx": 16384,
            "specialist_tabular": "qwen2.5-coder:7b", "tabular_temp": 0.0, "tabular_ctx": 16384,
            "specialist_narrative": "gemma2:27b", "narrative_temp": 0.1, "narrative_ctx": 32768
        }
    finally:
        db.close()

def get_active_model_name():
    return get_llm_config()["active_model"]
