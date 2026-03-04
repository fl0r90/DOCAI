from sqlalchemy.orm import Session
from ..models import AuditLog
from ..database import ForensicSessionLocal
import json

def log_event(
    action_type: str, 
    user_id: int = None, 
    details: dict | str = None, 
    severity: str = "INFO", 
    case_id: int = None
):
    """Salvează un eveniment de audit în Forensic DB."""
    db = ForensicSessionLocal()
    try:
        details_str = json.dumps(details) if isinstance(details, dict) else str(details)
        new_log = AuditLog(
            user_id=user_id,
            action_type=action_type,
            details=details_str,
            severity=severity,
            case_id=case_id
        )
        db.add(new_log)
        db.commit()
    except Exception as e:
        print(f"Failed to write audit log: {e}")
    finally:
        db.close()
