import os
import json
import re
import asyncio
import uuid
import requests
from typing import Dict, Any, List
from .llm_service import LLMService
from ..database import ForensicSessionLocal
from .. import models

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434")

def clean_val(val):
    if not val: return 0.0
    # Curățare robustă pentru formate financiare (ex: 1.234,56 sau 1,234.56)
    val = str(val).strip().replace(" ", "")
    if not val: return 0.0
    
    # Detecție format: dacă avem și punct și virgulă
    if ',' in val and '.' in val:
        # Verificăm care e ultimul (cel zecimal)
        if val.rfind(',') > val.rfind('.'):
            # Format European: 1.234,56
            val = val.replace(".", "").replace(",", ".")
        else:
            # Format US: 1,234.56
            val = val.replace(",", "")
    elif ',' in val:
        # Doar virgulă: 500,00 -> 500.00
        # Dar atenție la formatul 1,234 (fără zecimale, unde virgula e mii)
        # Heuristică: dacă sunt 3 cifre după virgulă la final, probabil e separator de mii
        if re.search(r',\d{3}$', val):
            val = val.replace(",", "")
        else:
            val = val.replace(",", ".")
            
    try: return float(val)
    except: return 0.0

def _unload_ollama():
    """VRAM Marshalling: Îi spunem Ollama să elibereze memoria pentru Docling."""
    try:
        print("[*] VRAM Marshalling: Detecție și eliberare modele Ollama...")
        # 1. Încercăm să obținem lista de modele active din Ollama
        res = requests.get(f"{OLLAMA_URL}/api/ps", timeout=5)
        if res.status_code == 200:
            models_info = res.json().get("models", [])
            for m in models_info:
                m_name = m.get("name")
                if m_name:
                    print(f"[*] Descărcare model activ: {m_name}")
                    requests.post(f"{OLLAMA_URL}/api/generate", json={"model": m_name, "keep_alive": 0}, timeout=5)
        
        # 2. Descarcă și modelele din configurație ca fallback
        from ..core.config import get_llm_config
        try:
            cfg = get_llm_config()
            models_to_unload = [
                cfg.get("active_model"), 
                cfg.get("specialist_narrative"), 
                cfg.get("specialist_tabular"),
                "gemma4:e4b"
            ]
            for m_name in filter(None, models_to_unload):
                requests.post(f"{OLLAMA_URL}/api/generate", json={"model": m_name, "keep_alive": 0}, timeout=5)
        except Exception as e:
            print(f"[!] Eroare la citirea configurării pentru descărcare LLM: {e}")
    except Exception as e:
        print(f"[!] Eroare generală VRAM Marshalling: {e}")

def _save_transaction_live(doc_id: int, data: str, desc: str, suma: float):
    """Salvează imediat tranzacția în DB."""
    db = ForensicSessionLocal()
    try:
        pg_id = str(uuid.uuid4())
        new_item = models.FinancialItem(
            id=pg_id,
            document_id=doc_id,
            transaction_date=str(data),
            description=str(desc),
            amount=suma,
            currency="RON"
        )
        db.add(new_item)
        db.commit()
    except Exception as e:
        print(f"[!] Eroare DB Live: {e}")
        db.rollback()
    finally:
        db.close()

async def extract_entities_from_table(md_content: str, llm: LLMService, context: str = "", model: str = "gemma4:e4b") -> Dict:
    """Extracție AGNOSTICĂ de entități din tabele Markdown."""
    prompt = f"""[INST] You are a Forensic Data Expert. Analyze the following table and extract all entities.
CONTEXT: {context}

Return ONLY valid JSON in this exact structure:
{{
    "entities": [
        {{"valoare": "Nume/CUI/IBAN", "tip_entitate": "PERSOANA|FIRMA|IBAN|CUI", "rol": "ex: Participant, Instructor, Beneficiar"}}
    ],
    "metadata": {{
        "table_type": "ex: Attendance List, Bank Statement, Invoice",
        "total_rows": 20
    }}
}}
RULES:
1. If the table contains people (Attendance/Participants), extract them as PERSOANA.
2. If it contains financial data, extract the parties involved.
3. Be precise with names. Clean any noise.

TABLE CONTENT:
{md_content}
[/INST]"""
    try:
        result = await asyncio.wait_for(llm.generate(prompt, model, is_json=True), timeout=120.0)
        return result
    except Exception as e:
        print(f"[!] Eroare LLM Extracție Tabel Agnostic: {e}")
        return {"entities": []}

async def extract_document_overview(doc_text: str, filename: str, llm: LLMService, model: str) -> Dict[str, Any]:
    """Extrage tipul de document, numărul, data, sinteza și un dicționar deschis/dinamic de atribute_specifice."""
    prompt = f"""### System:
Ești un Expert Auditor Forensic de Date. Analizează conținutul documentului și extrage metadatele esențiale.
Documentul poate fi de orice natură (registru prezență, curs, extras cont, factură, contract, proces-verbal, fișă utilaj, decizie, declarație, etc.).
Creează un dicționar deschis și dinamic de 'atribute_specifice' cu proprietățile pe care le consideri cele mai importante pentru anchetă.

Returnează DOAR un JSON valid cu această structură:
{{
    "tip_document": "ex: REGISTRU_CURS | FACTURA | EXTRAS_CONT | CONTRACT | PROCES_VERBAL | FISA_UTILAJ | DECLARATIE",
    "numar_document": "cod / număr sau null",
    "data_document": "YYYY-MM-DD sau DD-MM-YYYY sau null",
    "sinteza": "Rezumat executiv de 1-2 fraze despre ce reprezintă documentul și datele esențiale.",
    "atribute_specifice": {{
        "<cheie_relevanta_1>": "valoare",
        "<cheie_relevanta_2>": "valoare"
    }},
    "entitati_principale": [
        {{"nume": "...", "rol": "ex: Furnizor, Client, Instructor, Participant, Emitent, Beneficiar", "tip": "PERSOANA|FIRMA|IBAN|CUI|LOCATIE"}}
    ]
}}

### User:
NUME FISIER: {filename}
CONTINUT DOCUMENT:
{doc_text[:6000]}
"""
    try:
        res = await asyncio.wait_for(llm.generate(prompt, model, is_json=True), timeout=120.0)
        if isinstance(res, dict):
            return res
    except Exception as e:
        print(f"[!] Eroare LLM extract_document_overview ({filename}): {e}")
    return {}

async def extract_forensic_data(layout_data: Dict, filename: str = "", doc_id: int = 0, current_metadata: dict = None, start_segment: int = 0):
    """Procesare HIBRIDĂ AGNOSTICĂ cu Schemă Dinamică (Open-World Key-Value), VRAM Marshalling și Scriere Live."""
    import redis
    from .entity_resolver import save_entities_to_db
    from ..core.config import get_llm_config
    
    r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
    llm = LLMService()
    
    cfg = get_llm_config()
    model = cfg.get("active_model") or "gemma4:e4b"
    
    # 1. Extragere text global pentru analiză macro
    full_text = ""
    if isinstance(layout_data, dict):
        full_text = layout_data.get("markdown") or ""
        if not full_text:
            chunks = layout_data.get("chunks", [])
            full_text = "\n".join([c.get("content", "") for c in chunks[:15]])
    elif isinstance(layout_data, str):
        full_text = layout_data
        
    global_context = full_text[:600]

    # Pasul 1: Extracție Macro a Tipului de Document, Sintezei și Atributelor Dinamice
    r.set(f"doc_progress_{doc_id}", json.dumps({
        "status": "PROCESSING",
        "percent": 55,
        "message": f"Extracție atribute dinamice & clasificare ({filename})..."
    }))
    
    overview = await extract_document_overview(full_text, filename, llm, model)
    
    all_entities = []
    
    # Salvare imediată atribute macro & entități principale
    if overview:
        main_ents = overview.get("entitati_principale", [])
        save_entities_to_db({
            "metadata": {
                "tip_document": overview.get("tip_document"),
                "numar": overview.get("numar_document"),
                "data": overview.get("data_document")
            },
            "analysis": {
                "summary": overview.get("sinteza")
            },
            "entitati": main_ents,
            "dynamic_attributes": overview.get("atribute_specifice", {})
        }, doc_id)
        all_entities.extend(main_ents)

    # Pasul 2: Extracție granulară din tabele (dacă există)
    items = layout_data.get("items", []) if isinstance(layout_data, dict) else []
    table_items = [it for it in items if it.get("type") in ["TABLE", "TABLE_PART"]]
    total_tables = len(table_items)
    
    if total_tables > 0:
        print(f"[*] Extracție tabulară live ({filename}) - {total_tables} tabele găsite.")
        for idx, item in enumerate(table_items):
            r.set(f"doc_progress_{doc_id}", json.dumps({
                "status": "PROCESSING",
                "percent": round(60 + (idx / total_tables) * 30, 1),
                "message": f"Analiză tabel ({idx+1}/{total_tables})"
            }))
            table_res = await extract_entities_from_table(item["content"], llm, context=global_context, model=model)
            formatted_data = {
                "entitati": [
                    {"nume": e["valoare"], "rol": e.get("rol", "Participant"), "tip": e.get("tip_entitate", "PERSOANA")} 
                    for e in table_res.get("entities", [])
                ]
            }
            save_entities_to_db(formatted_data, doc_id)
            all_entities.extend(table_res.get("entities", []))

    res = {
        "doc_type": overview.get("tip_document", "GENERAL"),
        "doc_number": overview.get("numar_document"),
        "doc_date": overview.get("data_document"),
        "ai_summary": overview.get("sinteza"),
        "dynamic_attributes": overview.get("atribute_specifice", {}),
        "financial_data": [],
        "graph_data": {"entitati": all_entities, "relatii": []},
        "segment_summaries": []
    }

    await llm.close()
    return {"metadata": res, "is_finished": True}
