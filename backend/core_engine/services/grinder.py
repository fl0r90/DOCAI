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

async def extract_forensic_data(layout_data: Dict, filename: str = "", doc_id: int = 0, current_metadata: dict = None, start_segment: int = 0):
    """Procesare HIBRIDA AGNOSTICA cu VRAM Marshalling si Scriere Live."""
    import redis
    from .entity_resolver import save_entities_to_db # Importăm salvatorul robust
    from ..core.config import get_llm_config
    
    r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
    llm = LLMService()
    
    cfg = get_llm_config()
    model = cfg.get("specialist_tabular") or cfg.get("active_model") or "gemma4:e4b"
    
    # Contextul global pentru a ajuta LLM-ul să înțeleagă rolurile
    global_context = layout_data.get("chunks", [{}])[0].get("text", "")[:500] if isinstance(layout_data, dict) else ""

    res = {
        "doc_type": "HIBRID_AGNOSTIC_V3",
        "financial_data": [],
        "graph_data": {"entitati": [], "relatii": []},
        "segment_summaries": []
    }

    items = layout_data.get("items", []) if isinstance(layout_data, dict) else [{"type": "TEXT", "content": layout_data}]
    total_items = len(items)
    
    print(f"[*] Ingestie AGNOSTICA Live ({filename}) - {total_items} elemente.")

    for idx, item in enumerate(items):
        # Update UI Status
        r.set(f"doc_progress_{doc_id}", json.dumps({
            "status": "PROCESSING",
            "percent": round((idx / total_items) * 100, 1),
            "message": f"Analiză {item['type']} ({idx+1}/{total_items})"
        }))

        if item["type"] in ["TABLE", "TABLE_PART"]:
            # Extracție AGNOSTICĂ din tabel
            table_res = await extract_entities_from_table(item["content"], llm, context=global_context, model=model)
            
            # Mapăm rezultatele în formatul acceptat de save_entities_to_db
            formatted_data = {
                "entitati": [
                    {"nume": e["valoare"], "rol": e["rol"], "tip": e["tip_entitate"]} 
                    for e in table_res.get("entities", [])
                ]
            }
            # Salvare imediată în SQL/Neo4j
            save_entities_to_db(formatted_data, doc_id)
            
            # Păstrăm și în obiectul de retur pentru metadate doc
            res["graph_data"]["entitati"].extend(table_res.get("entities", []))

        elif item["type"] == "TEXT":
            text = item["content"]
            if len(text) > 100:
                try:
                    prompt = f"""### System:
Ești un Expert Analyst Forensic. Extrage Entități și Relații.
Returnează UNICUL obiect JSON valid:
{{
    "entitati": [
        {{"nume": "...", "tip": "FIRMA|PERSOANA|IBAN|CUI", "rol": "..."}}
    ]
}}
### User:
TEXT: {text[:3000]}
"""
                    ai_res = await asyncio.wait_for(llm.generate(prompt, model, is_json=True), timeout=180.0)
                    if ai_res:
                        save_entities_to_db(ai_res, doc_id)
                        res["graph_data"]["entitati"].extend(ai_res.get("entitati", []))
                except: pass

    await llm.close()
    return {"metadata": res, "is_finished": True}


    await llm.close()
    return {"metadata": res, "is_finished": True}
