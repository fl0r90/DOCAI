import os
import json
import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy.orm import Session
from ..models import AuditLog
from ..database import ForensicSessionLocal

# Asigurăm că folderul de loguri există
LOG_DIR = "/app/logs"
if not os.path.exists(LOG_DIR):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except:
        LOG_DIR = "./logs"
        os.makedirs(LOG_DIR, exist_ok=True)

# Setare culori ANSI pentru terminal/log
COLORS = {
    "INFO": "\033[94m",    # Albastru
    "SUCCESS": "\033[92m", # Verde
    "WARNING": "\033[93m", # Galben
    "ERROR": "\033[91m",   # Roșu
    "CRITICAL": "\033[95m",# Magenta
    "RESET": "\033[0m"
}

class ColorFormatter(logging.Formatter):
    def format(self, record):
        color = COLORS.get(record.levelname, COLORS["RESET"])
        record.msg = f"{color}{record.msg}{COLORS['RESET']}"
        return super().format(record)

logger = logging.getLogger("ForensicAudit")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    # 1. Console Handler (Colorat)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(ColorFormatter('%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(ch)

    # 2. File Handler (Rotație 10MB, max 5 fișiere) - Ne-colorat în fișier de obicei, dar îl lăsăm text simplu ca să fie lizibil.
    fh = RotatingFileHandler(os.path.join(LOG_DIR, "backend.log"), maxBytes=10*1024*1024, backupCount=5)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(fh)

def log_event(
    action_type: str, 
    user_id: int = None, 
    details: dict | str = None, 
    severity: str = "INFO", 
    case_id: int = None
):
    """Salvează un eveniment de audit în Forensic DB și în logul fizic."""
    details_str = json.dumps(details) if isinstance(details, dict) else str(details)
    
    # 1. Log fizic
    log_msg = f"Action: {action_type} | User: {user_id} | Case: {case_id} | Details: {details_str}"
    if severity == "ERROR": logger.error(log_msg)
    elif severity == "WARNING": logger.warning(log_msg)
    elif severity == "SUCCESS": logger.info(log_msg) # Considerăm SUCCESS ca INFO dar cu culoare diferită
    else: logger.info(log_msg)

    # 2. Log în baza de date
    db = ForensicSessionLocal()
    try:
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
        logger.error(f"Failed to write audit log to DB: {e}")
    finally:
        db.close()

