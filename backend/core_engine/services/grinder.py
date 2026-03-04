import os
import requests
import json
import re
import time
import redis
from ..core.config import get_llm_config

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434")
CHUNK_SIZE = 8000 

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
r = redis.from_url(redis_url)

def _unload_all_models():
    """Eliberare forțată a VRAM-ului."""
    try:
        res = requests.get(f"{OLLAMA_URL}/api/ps")
        if res.status_code == 200:
            for m in res.json().get("models", []):
                requests.post(f"{OLLAMA_URL}/api/generate", json={"model": m['name'], "keep_alive": 0}, timeout=5)
        print("[*] VRAM Eliberat pentru prioritate chat.")
    except: pass

def _send_to_ollama(model: str, prompt: str, timeout: int, is_json: bool = False, keep_warm: bool = True):
    try:
        keep_alive = 300 if keep_warm else 0
        res = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": model, "prompt": prompt, "stream": False, 
            "options": {"temperature": 0}, 
            "keep_alive": keep_alive 
        }, timeout=timeout)
        res.raise_for_status()
        raw = res.json().get("response", "")
        if not is_json: return raw
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        return json.loads(match.group(0)) if match else {}
    except Exception as e:
        print(f"[-] AI Error: {e}")
        return {} if is_json else ""

def classify_document_with_ai(text: str, model: str):
    if r.exists("llm_active_session"):
        _unload_all_models()
        return "ALTUL"
    sample = text[:4000]
    prompt = f"Analyze text and determine type: FACTURA, CONTRACT, BALANTA, OP, ALTUL. TEXT: {sample}\nReturn ONLY the category name."
    category = _send_to_ollama(model, prompt, 300, keep_warm=True)
    return str(category).strip().upper()

def extract_forensic_data(full_text: str, filename: str, doc_id: int, current_metadata: dict = None, start_segment: int = 0):
    """Extracție Agnostică (Roluri Funcționale)."""
    config = get_llm_config()
    
    doc_type = "ALTUL"
    if current_metadata and current_metadata.get("doc_type"):
        doc_type = current_metadata["doc_type"]
    else:
        doc_type = classify_document_with_ai(full_text, config["active_model"])
    
    is_tabular = doc_type in ["FACTURA", "BALANTA", "OP"]
    extract_model = config["specialist_tabular"] if is_tabular else config["specialist_narrative"]
    
    text_chunks = [full_text[i:i + CHUNK_SIZE] for i in range(0, len(full_text), CHUNK_SIZE)]
    consolidated = current_metadata or {"furnizor": {}, "client": {}, "total": 0.0, "articole": [], "parti": [], "data_document": "", "obiect": ""}
    
    print(f"[*] Lansare Ingestie Agnostică ({extract_model}) - Tip: {doc_type}")
    
    for idx in range(start_segment, len(text_chunks)):
        if r.exists("llm_active_session"):
            _unload_all_models()
            return {"doc_type": doc_type, "metadata": consolidated, "next_segment": idx, "is_finished": False}

        chunk = text_chunks[idx]
        print(f"[*] Segment {idx+1}/{len(text_chunks)}...")
        
        if is_tabular:
            prompt = f"""
            Identifică datele financiare din acest segment de {doc_type}. 
            1. EMITENT (Actor A): Cine furnizează serviciul (Furnizor, Operator, Prestator).
            2. RECEPTOR (Actor B): Cine primește serviciul (Client, Abonat, Titular).
            3. DATA: Când a fost emis/semnat.
            4. VALOARE: Suma totală.
            
            TEXT: {chunk}
            Return ONLY JSON: {{"furnizor": {{"nume": "", "cui": ""}}, "client": {{"nume": "", "cui": ""}}, "total": 0.0, "data_document": "DD.MM.YYYY", "articole": []}}
            """
        else:
            prompt = f"""
            Analizează acest segment de CONTRACT/LEGAL.
            1. PĂRȚI: Identifică entitățile sau persoanele implicate și rolul lor.
            2. DATA: Data încheierii sau intrării în vigoare.
            3. OBIECT: Scopul actului.
            
            TEXT: {chunk}
            Return ONLY JSON: {{"parti": [{{"nume": "", "rol": ""}}], "obiect": "", "data_document": "DD.MM.YYYY"}}
            """

        segment_data = _send_to_ollama(extract_model, prompt, 1200, is_json=True, keep_warm=True)
        
        # Consolidare inteligentă
        if segment_data.get("data_document"): consolidated["data_document"] = segment_data["data_document"]
        if segment_data.get("furnizor", {}).get("nume"): consolidated["furnizor"] = segment_data["furnizor"]
        if segment_data.get("client", {}).get("nume"): consolidated["client"] = segment_data["client"]
        if segment_data.get("obiect"): consolidated["obiect"] = segment_data["obiect"]
        
        for art in segment_data.get("articole", []): consolidated["articole"].append(art)
        for p in segment_data.get("parti", []): 
            if not any(ex["nume"] == p["nume"] for ex in consolidated["parti"]):
                consolidated["parti"].append(p)
        
        r.set(f"doc_progress_{doc_id}", json.dumps({"metadata": consolidated, "last_idx": idx}))

    # Sinteză Finală Agnostică
    _unload_all_models()
    summary_prompt = f"""
    Ești un expert auditor. Fă un rezumat ultra-scurt (o frază) pentru {filename}. 
    Format obligatoriu: 'Document de tip [Tip] între [Actor A] și [Actor B], emis la data de [Data], cu valoarea de [Suma].'
    Dacă un element lipsește, scrie 'nespecificat'.
    DATE: {json.dumps(consolidated)}
    """
    summary = _send_to_ollama(config["specialist_narrative"], summary_prompt, 300, keep_warm=False)
    
    r.delete(f"doc_progress_{doc_id}")
    return {"doc_type": doc_type, "metadata": consolidated, "summary": summary, "is_finished": True}
