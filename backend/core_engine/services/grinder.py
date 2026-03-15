import os
import requests
import json
import re
import time
import redis
from ..core.config import get_llm_config

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434")
CHUNK_SIZE = 1500 

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.from_url(redis_url)

def _unload_all_models():
    """Golește complet VRAM-ul pentru a face loc următorului model."""
    try:
        res = requests.get(f"{OLLAMA_URL}/api/ps")
        if res.status_code == 200:
            for m in res.json().get("models", []):
                requests.post(f"{OLLAMA_URL}/api/generate", json={"model": m['name'], "keep_alive": 0}, timeout=5)
        print("[*] VRAM Marshalling: Memorie video eliberată.")
    except Exception as e:
        print(f"[!] Eroare eliberare VRAM: {e}")

def _send_to_ollama(model: str, prompt: str, timeout: int, is_json: bool = False, keep_warm: bool = True):
    """Trimite cererea și extrage JSON-ul manual pentru stabilitate maximă."""
    try:
        safe_prompt = "".join(c for c in prompt if c.isprintable() or c in "\n\r\t")
        keep_alive = 300 if keep_warm else 0
        payload = {
            "model": model, 
            "prompt": safe_prompt, 
            "stream": False, 
            "options": {"temperature": 0.01}, # Temperatura minima pentru structura rigida
            "keep_alive": keep_alive
        }
        if is_json:
            payload["format"] = "json"
            
        res = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=timeout)
        res.raise_for_status()
        raw = res.json().get("response", "")
        if not is_json: return raw
        
        # 1. Curățare zgomot (think tags)
        clean = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)
        
        # 2. Sanitizare agresivă JSON (ghilimele invalide în descrieri)
        # Căutăm câmpul "descriere": "..." și curățăm ghilimelele duble interne
        def sanitize_json_string(match):
            key_val = match.group(0)
            if '"descriere":' in key_val or '"valoare":' in key_val:
                # Extragem textul dintre prima și ultima ghilimea de valoare
                parts = key_val.split('": "', 1)
                if len(parts) == 2:
                    content = parts[1].rsplit('"', 1)[0]
                    # Înlocuim ghilimelele duble interne cu simple
                    sanitized_content = content.replace('"', "'")
                    return f'"{parts[0]}": "{sanitized_content}"'
            return key_val

        # Regex pentru a găsi perechi cheie-valoare string
        sanitized_json = re.sub(r'"[^"]+":\s*"[^"]*"', sanitize_json_string, clean)

        try:
            return json.loads(sanitized_json)
        except:
            # Ultimul resort: json.loads pe textul curățat de caractere de control
            try:
                final_clean = "".join(c for c in clean if ord(c) >= 32 or c in "\n\r\t")
                return json.loads(final_clean)
            except: pass
        return {}
    except Exception as e:
        print(f"[-] AI Error ({model}): {e}")
        return {} if is_json else ""

def classify_document_with_ai(text: str, model: str):
    if r.exists("llm_active_session"):
        _unload_all_models()
        return "ALTUL"
    sample = text[:4000]
    prompt = f"""### System:
Expert Document Classifier.
Identify category: FACTURA, CONTRACT, BALANTA, OP, DISPOZITIV_MOBIL, ALTUL.
### User:
TEXT: {sample}
Return ONLY the category name.
### Assistant:
"""
    category = _send_to_ollama(model, prompt, 300, keep_warm=True)
    return str(category).strip().upper()

def extract_forensic_data(full_text: str, filename: str, doc_id: int, current_metadata: dict = None, start_segment: int = 0):
    """Extracție de înaltă precizie cu controlul integrității (CRC)."""
    config = get_llm_config()
    _unload_all_models()
    
    doc_type = "ALTUL"
    if current_metadata and current_metadata.get("doc_type"):
        doc_type = current_metadata["doc_type"]
    else:
        doc_type = classify_document_with_ai(full_text, config["active_model"])
    
    is_tabular = doc_type in ["FACTURA", "BALANTA", "OP"]
    extract_model = config["specialist_tabular"] if is_tabular else config["specialist_narrative"]
    
    text_chunks = [full_text[i:i + CHUNK_SIZE] for i in range(0, len(full_text), CHUNK_SIZE)]
    total_segments = len(text_chunks)
    
    if not current_metadata:
        consolidated = {
            "doc_type": doc_type,
            "data_document": "",
            "graph_data": {"entitati": [], "relatii": []},
            "financial_data": [],
            "failed_segments": []
        }
    else:
        consolidated = current_metadata
        if "graph_data" not in consolidated: consolidated["graph_data"] = {"entitati": [], "relatii": []}
        if "financial_data" not in consolidated: consolidated["financial_data"] = []
        if "failed_segments" not in consolidated: consolidated["failed_segments"] = []
    
    print(f"[*] Lansare Ingestie Forensic (CRC Active) - Model: {extract_model} - Segmente: {total_segments}")
    
    for idx in range(start_segment, total_segments):
        if r.exists("llm_active_session"):
            _unload_all_models()
            return {"doc_type": doc_type, "metadata": consolidated, "next_segment": idx, "is_finished": False, "total_segments": total_segments}

        chunk = text_chunks[idx]
        print(f"[*] Analiza Segment {idx+1}/{total_segments}...")
        
        system_msg = f"Expert Forensic Auditor. Misiune: Extracție structurată (JSON) din segment de document tip {doc_type}."
        user_msg = f"""Obiectiv: Extrage toate entitățile și tranzacțiile financiare identificate.
Schema JSON obligatorie:
{{
    "data_document": "YYYY-MM-DD",
    "entitati": [{{"id": "e1", "tip_entitate": "Persoana|Firma|IBAN|Telefon", "valoare": "Value", "rol": "Context"}}],
    "tranzactii": [{{"descriere": "Detaliu tranzacție", "suma": 0.0, "valuta": "RON"}}]
}}
Fragment Text:
{chunk}"""

        # Format universal de prompt (System/User/Assistant)
        prompt = f"### System:\n{system_msg}\n\n### User:\n{user_msg}\n\n### Assistant:\n"

        segment_data = None
        for attempt in range(2): # 2 încercări total
            try:
                segment_data = _send_to_ollama(extract_model, prompt, 1200, is_json=True, keep_warm=True)
                if segment_data and (segment_data.get("tranzactii") or segment_data.get("entitati") or "data_document" in segment_data):
                    break
                print(f"[?] Segment {idx+1} invalid. Re-incercare {attempt+1}...")
                time.sleep(2)
            except Exception as e:
                print(f"[!] Tentativa {attempt+1} esuata pentru {idx+1}: {e}")
                time.sleep(3)

        if not segment_data:
            print(f"[!] ESEC DEFINITIV SEGMENT {idx+1}")
            consolidated["failed_segments"].append({"idx": idx, "error": "AI Timeout/Invalid JSON"})
            continue

        try:
            if segment_data.get("data_document"): consolidated["data_document"] = segment_data["data_document"]
            
            for ent in segment_data.get("entitati", []):
                val = ent.get("valoare") or ent.get("nume") or ent.get("name")
                tip = ent.get("tip_entitate", "")
                if not val: continue
                if tip == "IBAN" and re.match(r'^[0-9.,-]+$', str(val)): continue
                if not any(ex["valoare"] == val for ex in consolidated["graph_data"]["entitati"]):
                    ent["valoare"] = val
                    consolidated["graph_data"]["entitati"].append(ent)
            
            for rel in segment_data.get("relatii", []):
                consolidated["graph_data"]["relatii"].append(rel)
                
            for trans in segment_data.get("tranzactii", []):
                consolidated["financial_data"].append(trans)
                
        except Exception as e:
            print(f"[!] ESEC SEGMENT {idx+1}: {e}")
            consolidated["failed_segments"].append({"idx": idx, "error": str(e)})
        
        r.set(f"doc_progress_{doc_id}", json.dumps({"metadata": consolidated, "last_idx": idx}))

    _unload_all_models()
    summary_prompt = f"""### System:
Expert Forensic Auditor.
Misiune: Generare rezumat executiv, tehnic și concis în ROMÂNĂ.
### User:
Document: {filename}
Date Extrase: {json.dumps(consolidated)}
### Assistant:
"""
    summary = _send_to_ollama(config["specialist_narrative"], summary_prompt, 300, keep_warm=False)
    
    r.delete(f"doc_progress_{doc_id}")
    return {
        "doc_type": doc_type, "metadata": consolidated, 
        "graph_data": consolidated["graph_data"],
        "summary": summary, "is_finished": True,
        "total_segments": total_segments,
        "failed_segments": consolidated["failed_segments"]
    }
