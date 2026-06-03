from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_forensic_db, ForensicSessionLocal, get_auth_db, SessionLocal
from ..models import Case, User, Document, ChatMessage, case_worker_link, MasterEntity, DocumentEntityLink, DocumentChunk, FinancialItem
from ..core.security import SECRET_KEY, ALGORITHM
from jose import jwt, JWTError
from ..core.audit import log_event
from ..services.chat_service import query_investigator
from ..services.graph_service import graph_service
from ..core.config import get_active_model_name
import requests
import json
import os
from fpdf import FPDF
from datetime import datetime
import redis

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
r_client = redis.from_url(redis_url)

router = APIRouter(prefix="/cases", tags=["cases"])

class CaseCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ChatRequest(BaseModel):
    question: str

def get_current_user(authorization: str = Header(None), token: Optional[str] = None, db: Session = Depends(get_auth_db)):
    final_token = None
    if authorization and authorization.startswith("Bearer "):
        final_token = authorization.split(" ")[1]
    elif token:
        final_token = token
        
    if not final_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    try:
        payload = jwt.decode(final_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError: raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.username == username).first()
    if user is None: raise HTTPException(status_code=401, detail="User not found")
    return user

def validate_case_access(case_id: int, user: User, db: Session):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case: raise HTTPException(status_code=404, detail="Case not found")
    if user.role == "ADMIN": return case
    if user.role == "MASTER" and case.master_id == user.id: return case
    is_assigned = db.query(case_worker_link).filter(
        case_worker_link.c.case_id == case_id,
        case_worker_link.c.user_id == user.id
    ).first()
    if is_assigned: return case
    raise HTTPException(status_code=403, detail="Acces refuzat.")

@router.get("/")
def get_cases(current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    if current_user.role == "ADMIN":
        cases = db.query(Case).all()
    elif current_user.role == "MASTER":
        cases = db.query(Case).filter(Case.master_id == current_user.id).all()
    else:
        assigned_ids = [r[0] for r in db.query(case_worker_link.c.case_id).filter(case_worker_link.c.user_id == current_user.id).all()]
        cases = db.query(Case).filter(Case.id.in_(assigned_ids)).all()
    return [{
        "id": c.id, "name": c.name, "description": c.description, "status": c.status,
        "document_count": len(c.documents), "created_at": c.created_at
    } for c in cases]

@router.post("/")
def create_case(case_in: CaseCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    if current_user.role not in ["ADMIN", "MASTER"]:
        raise HTTPException(status_code=403, detail="Permisiuni insuficiente.")
    new_case = Case(name=case_in.name, description=case_in.description, master_id=current_user.id)
    db.add(new_case); db.commit(); db.refresh(new_case)
    log_event("CASE_CREATED", user_id=current_user.id, case_id=new_case.id, details={"name": new_case.name})
    return new_case

@router.post("/{case_id}/delete")
def delete_case(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    c = db.query(Case).filter(Case.id == case_id).first()
    if not c: raise HTTPException(status_code=404, detail="Case not found")
    
    # Verificare permisiuni (Doar Admin sau Master-ul dosarului)
    if current_user.role != "ADMIN" and c.master_id != current_user.id:
        raise HTTPException(status_code=403, detail="Nu aveți dreptul să ștergeți acest dosar.")

    # 1. Ștergere Documente în Cascadă (folosind logica existentă pentru fiecare document)
    docs = db.query(Document).filter(Document.case_id == case_id).all()
    for doc in docs:
        filename = doc.filename
        doc_id = doc.id
        
        # Stergere Neo4j
        try: graph_service.delete_document(doc_id)
        except: pass
        
        # Stergere dependente SQL
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete()
        db.query(FinancialItem).filter(FinancialItem.document_id == doc_id).delete()
        db.query(DocumentEntityLink).filter(DocumentEntityLink.document_id == doc_id).delete()
        
        # Stergere disc
        paths = [os.path.join("/app/uploads", filename), os.path.join("/app/backend/uploads", filename)]
        for p in paths:
            if os.path.exists(p):
                try: os.remove(p)
                except: pass

    # 2. Ștergere Chat și Case din SQL
    db.query(ChatMessage).filter(ChatMessage.case_id == case_id).delete()
    db.delete(c)
    db.commit()
    
    # 3. Ștergere nod Case din Neo4j (dacă există)
    if graph_service.driver:
        try:
            with graph_service.driver.session() as session:
                session.run("MATCH (c:Case {id: $id}) DETACH DELETE c", id=case_id)
        except: pass

    log_event("CASE_DELETED", user_id=current_user.id, case_id=case_id, details={"case_name": c.name})
    return {"message": "Dosar șters complet din toate sistemele."}

@router.get("/{case_id}/documents")
def get_case_documents(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    validate_case_access(case_id, current_user, db)
    return db.query(Document).filter(Document.case_id == case_id).order_by(Document.created_at.desc()).all()

@router.get("/{case_id}/entities")
def get_case_entities(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    validate_case_access(case_id, current_user, db)
    return db.query(MasterEntity).join(DocumentEntityLink).join(Document).filter(Document.case_id == case_id).distinct().all()

@router.get("/{case_id}/graph")
def get_case_graph(case_id: int, current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    try: validate_case_access(case_id, current_user, db)
    finally: db.close()
    
    if not graph_service.driver: raise HTTPException(status_code=503, detail="Graph DB unavailable")
    with graph_service.driver.session() as session:
        result = session.run("""
            MATCH (c:Case {id: $case_id})<-[:PARTE_DIN]-(d:Document)
            OPTIONAL MATCH (d)<-[r:APARE_IN]-(e)
            OPTIONAL MATCH (e)-[:LOCALIZAT_LA]->(loc:Locatie)
            RETURN c, d, e, r, loc, id(e) as eid, id(loc) as lid
        """, case_id=case_id)
        
        nodes = {}
        links = []
        for record in result:
            c = record["c"]
            c_key = f"c_{c['id']}"
            if c_key not in nodes:
                nodes[c_key] = {"id": c_key, "label": "CASE", "name": c["name"], "color": "#3b82f6"}
            d = record["d"]
            if d:
                d_key = f"d_{d['id']}"
                if d_key not in nodes:
                    nodes[d_key] = {"id": d_key, "label": "DOC", "name": d["filename"], "color": "#f97316"}
                    links.append({"source": d_key, "target": c_key})
                e = record["e"]
                if e:
                    label = list(e.labels)[0]
                    # Folosim ID numeric simplu
                    e_key = f"e_{record['eid']}"
                    if e_key not in nodes:
                        nodes[e_key] = {"id": e_key, "label": label.upper(), "name": e["name"], "color": "#ef4444" if label=="Firma" else "#eab308"}
                    if not any(l["source"] == e_key and l["target"] == d_key for l in links):
                        links.append({"source": e_key, "target": d_key})
                    loc = record["loc"]
                    if loc:
                        l_key = f"l_{record['lid']}"
                        if l_key not in nodes:
                            nodes[l_key] = {"id": l_key, "label": "LOC", "name": loc["adresa"], "color": "#10b981"}
                        if not any(l["source"] == e_key and l["target"] == l_key for l in links):
                            links.append({"source": e_key, "target": l_key})
        return {"nodes": list(nodes.values()), "links": links}

@router.get("/{case_id}/timeline")
def get_case_timeline(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    validate_case_access(case_id, current_user, db)
    
    # 1. Documente (folosim created_at ca dată de referință)
    docs = db.query(Document).filter(Document.case_id == case_id).all()
    events = []
    for d in docs:
        events.append({
            "id": f"doc_{d.id}",
            "date": d.created_at.strftime("%Y-%m-%d"),
            "type": "DOC_CREATED",
            "title": f"Document: {d.filename}",
            "description": f"Proba {d.filename} a fost introdusa in dosar.",
            "doc_name": d.filename
        })

    # 2. Tranzacții financiare
    transactions = db.query(FinancialItem).join(Document).filter(Document.case_id == case_id).all()
    for tr in transactions:
        try:
            d_parts = tr.transaction_date.split('.')
            if len(d_parts) == 3:
                iso_date = f"{d_parts[2]}-{d_parts[1]}-{d_parts[0]}"
                events.append({
                    "id": f"tr_{tr.id}",
                    "date": iso_date,
                    "type": "TRANSACTION",
                    "title": f"Tranzactie: {tr.amount} {tr.currency or 'RON'}",
                    "description": tr.description,
                    "doc_name": tr.doc_filename
                })
        except: continue
        
    events.sort(key=lambda x: (x['date'], x['type']))
    return events

# --- EXISTING ANALYTICS ROUTES ---

@router.get("/{case_id}/graph/analytics/leader")
def get_case_leader(case_id: int, current_user: User = Depends(get_current_user)):
    if not graph_service.driver: raise HTTPException(status_code=503, detail="Graph DB unavailable")
    with graph_service.driver.session() as session:
        result = session.run("""
            MATCH (c:Case {id: $case_id})<-[:PARTE_DIN]-(d:Document)<-[:APARE_IN]-(e)
            WITH e, count(d) as degree
            RETURN id(e) as id, degree
        """, case_id=case_id)
        return {f"e_{r['id']}": r["degree"] for r in result}

@router.get("/{case_id}/graph/analytics/cartel")
def get_case_cartel(case_id: int, current_user: User = Depends(get_current_user)):
    if not graph_service.driver: raise HTTPException(status_code=503, detail="Graph DB unavailable")
    with graph_service.driver.session() as session:
        result = session.run("""
            MATCH (c:Case {id: $case_id})<-[:PARTE_DIN]-(d:Document)<-[:APARE_IN]-(e)
            RETURN id(e) as id, id(e) % 5 as community
        """, case_id=case_id)
        return {f"e_{r['id']}": r["community"] for r in result}

@router.get("/{case_id}/graph/analytics/path")
def get_shortest_path(case_id: int, source_name: str, target_name: str, current_user: User = Depends(get_current_user)):
    if not graph_service.driver: raise HTTPException(status_code=503, detail="Graph DB unavailable")
    with graph_service.driver.session() as session:
        result = session.run("""
            MATCH (s {name: $s_name}), (t {name: $t_name})
            MATCH p = shortestPath((s)-[*]-(t))
            RETURN [n in nodes(p) | id(n)] as nodes
        """, s_name=source_name, t_name=target_name)
        record = result.single()
        if not record: return {"nodes": []}
        return {"nodes": [f"e_{nid}" for nid in record["nodes"]]}

@router.get("/{case_id}/graph/analytics/clones")
def get_clones(case_id: int, cui: str, current_user: User = Depends(get_current_user)):
    if not graph_service.driver: raise HTTPException(status_code=503, detail="Graph DB unavailable")
    with graph_service.driver.session() as session:
        result = session.run("""
            MATCH (e1 {cui: $cui})-[*2]-(e2)
            WHERE e1 <> e2 AND (e1.name <> e2.name OR e1.adresa = e2.adresa)
            RETURN id(e1) as s_id, id(e2) as c_id
        """, cui=cui)
        return {"clones": [{"suspect_id": f"e_{r['s_id']}", "clone_id": f"e_{r['c_id']}"} for r in result]}

# --- CHAT & SUMMARY ---

from fastapi.responses import StreamingResponse

@router.post("/{case_id}/chat/stop")
def stop_chat_generation(case_id: int, current_user: User = Depends(get_current_user)):
    r_client.set(f"chat_stop_{case_id}", "1", ex=60)
    return {"status": "Stop signal sent"}

@router.post("/{case_id}/chat")
def chat_with_case(case_id: int, payload: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    validate_case_access(case_id, current_user, db)
    
    # Resetăm semnalul de stop la începutul unei noi cereri
    r_client.delete(f"chat_stop_{case_id}")
    
    user_msg = ChatMessage(case_id=case_id, role="user", content=payload.question)
    db.add(user_msg); db.commit()
    
    # Folosim generatorul pentru Streaming
    from ..services.chat_service import AgenticInvestigator
    
    def stream_generator():
        try:
            print(f"[*] Pornim investigatia agentica pentru Case {case_id}...")
            agent = AgenticInvestigator(case_id, payload.question)
            full_answer = ""
            inv_log = []
            
            for chunk_json in agent.run():
                # Verificăm semnalul de stop în Redis
                if r_client.get(f"chat_stop_{case_id}"):
                    print(f"[!] Stop detectat pentru Case {case_id}. Întrerupem fluxul.")
                    yield json.dumps({"type": "final", "data": full_answer + "... [Oprit de utilizator]"}) + "\n"
                    break

                chunk = json.loads(chunk_json)
                if chunk["type"] == "final":
                    full_answer = chunk["data"]
                    print(f"[+] INVESTIGATIE FINALA: Răspuns final generat.")
                elif chunk["type"] == "step":
                    print(f"[*] AGENT PAS: {chunk['data']}")
                elif chunk["type"] == "status":
                    print(f"[*] AGENT STATUS: {chunk['data']}")
                elif chunk["type"] == "tool_call":
                    print(f"[*] AGENT APEL UNELTA: {chunk['tool']} cu parametrii: {chunk['params']}")
                elif chunk["type"] == "observation":
                    if chunk['data'].startswith("Thinking:"):
                        # Capturăm gândirea și planul strategic
                        print(f"[*] AGENT RATIONAMENT: {chunk['data'][9:300].strip()}...")
                    else:
                        obs_snippet = chunk['data'][:150].replace('\n', ' ')
                        print(f"[*] AGENT OBSERVATIE: {obs_snippet}...")
                else:
                    inv_log.append(chunk)
                
                # De asemenea, salvăm chunk-ul în log
                if chunk["type"] != "final":
                    inv_log.append(chunk)
                    
                yield chunk_json + "\n"
            
            # Salvăm răspunsul curat în baza de date
            if full_answer:
                with ForensicSessionLocal() as db_stream:
                    assistant_msg = ChatMessage(
                        case_id=case_id, 
                        role="assistant", 
                        content=full_answer,
                        sql=json.dumps(inv_log, ensure_ascii=False), # Salvăm logurile structurate în format JSON
                        citations=agent.citations
                    )
                    db_stream.add(assistant_msg)
                    db_stream.commit()
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[!] Eroare in stream_generator: {e}")
            yield json.dumps({"type": "final", "data": f"Eroare de comunicare internă: {str(e)}"}) + "\n"

    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

@router.get("/{case_id}/chat")
def get_chat_history(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    validate_case_access(case_id, current_user, db)
    return db.query(ChatMessage).filter(ChatMessage.case_id == case_id).order_by(ChatMessage.created_at.asc()).all()

@router.post("/{case_id}/chat/clear")
def clear_chat_history(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    validate_case_access(case_id, current_user, db)
    db.query(ChatMessage).filter(ChatMessage.case_id == case_id).delete()
    db.commit()
    return {"message": "Chat history cleared"}

@router.post("/{case_id}/chat/{message_id}/delete")
def delete_chat_message(case_id: int, message_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    validate_case_access(case_id, current_user, db)
    msg = db.query(ChatMessage).filter(ChatMessage.id == message_id, ChatMessage.case_id == case_id).first()
    if msg: db.delete(msg); db.commit()
    return {"message": "Deleted"}

from fastapi.responses import FileResponse

def generate_audit_report_pdf(case: Case, report_path: str):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, text=f"RAPORT DE AUDIT FORENSIC - DOSAR #{case.id}", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    pdf.cell(0, 10, text=f"Generat la: {now}", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    
    # Informații Dosar
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, text="1. INFORMATII DOSAR", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, text=f"Nume: {case.name}", new_x="LMARGIN", new_y="NEXT")
    desc = (case.description or "Nicio descriere").encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, text=f"Descriere: {desc}")
    pdf.ln(5)
    
    # Documente Procesate
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, text="2. PROBE MATERIALE (DOCUMENTE)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    for doc in case.documents:
        status_icon = "[OK]" if doc.status == "COMPLETED" else "[!!]"
        pdf.cell(0, 7, text=f"{status_icon} {doc.filename} - Status: {doc.status}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Sinteza AI
    if case.case_summary:
        pdf.set_font("Helvetica", 'B', 12)
        pdf.cell(0, 10, text="3. SINTEZA ANALITICA (AI)", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", 'I', 10)
        summary_clean = case.case_summary.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, text=summary_clean)
        pdf.ln(5)
    
    # Footer de Securitate
    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, text="--- DOCUMENT GENERAT AUTOMAT - DOCAI FORENSIC ENGINE ---", align='C', new_x="LMARGIN", new_y="NEXT")
    
    pdf.output(report_path)

@router.get("/{case_id}/audit-report")
def download_audit_report(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    print(f"[*] Cerere raport audit pentru Case {case_id} de catre {current_user.username}")
    validate_case_access(case_id, current_user, db)
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case: raise HTTPException(status_code=404, detail="Case not found")
    
    report_path = f"/app/uploads/Audit_Report_Case_{case_id}.pdf"
    
    # Generăm raportul dacă nu există sau dacă vrem să fie mereu proaspăt
    # (Pentru Alpha, îl generăm la fiecare cerere să fie up-to-date cu chat-ul/rezumatul)
    try:
        generate_audit_report_pdf(case, report_path)
    except Exception as e:
        print(f"[!] Eroare generare PDF: {e}")
        # Dacă generarea eșuează dar fișierul vechi există, îl dăm pe acela
        if not os.path.exists(report_path):
            raise HTTPException(status_code=500, detail=f"Eroare generare raport: {str(e)}")

    return FileResponse(report_path, filename=f"Raport_Audit_{case.name.replace(' ', '_')}.pdf", media_type="application/pdf")

@router.get("/{case_id}/summary")
def get_case_summary(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    validate_case_access(case_id, current_user, db)
    c = db.query(Case).filter(Case.id == case_id).first()
    
    # Dacă avem deja un rezumat, îl returnăm direct
    if c.case_summary and len(c.case_summary) > 10:
        return {"summary": c.case_summary}
        
    processed_docs = [d for d in c.documents if d.status == "COMPLETED" and d.ai_summary]
    if not processed_docs: return {"summary": "Dosarul nu are documente procesate."}
    summaries_text = "\n\n".join([f"DOC: {d.filename}\nSUMAR: {d.ai_summary}" for d in processed_docs])
    active_model = get_active_model_name()
    
    system_msg = "Senior Forensic Lead. Misiune: Generare Sinteză Executivă a dosarului."
    user_msg = f"Obiectiv: Realizează o analiză de ansamblu pentru dosarul '{c.name}', integrând următoarele rezumate de documente:\n{summaries_text}"
    prompt = f"### System:\n{system_msg}\n\n### User:\n{user_msg}\n\n### Assistant:\n"
    
    try:
        res = requests.post(f"http://llm:11434/api/generate", json={"model": active_model, "prompt": prompt, "stream": False}, timeout=1800)
        summary = res.json().get("response", "")
        c.case_summary = summary; db.commit()
        return {"summary": summary}
    except Exception as e: return {"summary": f"Eroare: {str(e)}"}

@router.get("/progress/{doc_id}")
def get_document_progress(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Document not found")
    validate_case_access(doc.case_id, current_user, db)
    
    data = r_client.get(f"doc_progress_{doc_id}")
    if data:
        progress = json.loads(data)
        # Eliminăm metadatele mari pentru a reduce traficul de rețea
        if "metadata" in progress: del progress["metadata"]
        return progress
        
    return {
        "status": doc.status,
        "percent": 100 if doc.status == "COMPLETED" else 0,
        "eta_seconds": 0,
        "current_segment": 0,
        "total_segments": 0
    }

@router.post("/documents/{doc_id}/pause")
def pause_document(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Document not found")
    validate_case_access(doc.case_id, current_user, db)
    
    if doc.status not in ["PAUSED", "FAILED", "COMPLETED"]:
        r_client.set(f"doc_prev_status_{doc_id}", doc.status)
        doc.status = "PAUSED"
        r_client.set(f"doc_pause_{doc_id}", "1")
        db.commit()
        log_event("DOCUMENT_PAUSED", user_id=current_user.id, case_id=doc.case_id, details={"filename": doc.filename})
    
    return {"status": "PAUSED"}

@router.post("/documents/{doc_id}/resume")
def resume_document(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Document not found")
    validate_case_access(doc.case_id, current_user, db)
    
    if doc.status == "PAUSED":
        prev_status = r_client.get(f"doc_prev_status_{doc_id}")
        doc.status = prev_status.decode() if prev_status else "QUEUED"
        r_client.delete(f"doc_pause_{doc_id}")
        db.commit()
        log_event("DOCUMENT_RESUMED", user_id=current_user.id, case_id=doc.case_id, details={"filename": doc.filename})
    
    return {"status": doc.status}

@router.post("/documents/{doc_id}/stop")
def stop_document(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Document not found")
    validate_case_access(doc.case_id, current_user, db)
    
    doc.status = "FAILED"
    r_client.set(f"doc_stop_{doc_id}", "1")
    r_client.delete(f"doc_pause_{doc_id}")
    db.commit()
    log_event("DOCUMENT_STOPPED", user_id=current_user.id, case_id=doc.case_id, details={"filename": doc.filename})
    
    return {"status": "FAILED"}

@router.post("/documents/{doc_id}/retry")
def retry_document(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    """Reîncepe procesarea unui document eșuat, curățând VRAM-ul și cache-ul."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Document not found")
    validate_case_access(doc.case_id, current_user, db)
    
    if doc.status not in ["FAILED", "PROCESSING", "COMPLETED"]:
        raise HTTPException(status_code=400, detail="Only failed, stuck, or completed documents can be retried")

    # 1. Curățare VRAM (Apelează funcția din ocr_service dacă există)
    try:
        from ..services.ocr_service import unload_vram
        unload_vram()
    except Exception as e:
        print(f"[!] Warning: VRAM cleanup failed during retry: {e}")

    # 2. Ștergere date vechi din DB pentru a evita duplicate
    try:
        db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete()
        db.query(FinancialItem).filter(FinancialItem.document_id == doc_id).delete()
        db.query(DocumentEntityLink).filter(DocumentEntityLink.document_id == doc_id).delete()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database cleanup failed: {e}")

    # 3. Resetare status
    doc.status = "QUEUED"
    doc.processing_progress = 0
    doc.doc_metadata = None
    doc.ai_summary = None
    r_client.delete(f"doc_progress_{doc_id}")
    r_client.delete(f"doc_stop_{doc_id}")
    r_client.delete(f"doc_pause_{doc_id}")
    
    db.commit()
    log_event("DOCUMENT_RETRY", user_id=current_user.id, case_id=doc.case_id, details={"filename": doc.filename}, severity="WARNING")
    
    return {"message": "Document re-queued for processing with clean VRAM.", "status": "QUEUED"}

@router.post("/documents/{doc_id}/delete")
def delete_document(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Document not found")
    validate_case_access(doc.case_id, current_user, db)
    
    filename = doc.filename
    case_id = doc.case_id

    # 1. Ștergere din Neo4j (Clean & Orphan Removal via GraphService)
    try:
        graph_service.delete_document(doc_id)
    except Exception as ge:
        print(f"[!] Eroare ștergere Graph: {ge}")

    # 2. Ștergere manuală dependențe SQL (pentru siguranță totală la re-upload)
    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).delete()
    db.query(FinancialItem).filter(FinancialItem.document_id == doc_id).delete()
    db.query(DocumentEntityLink).filter(DocumentEntityLink.document_id == doc_id).delete()
    
    # 3. Ștergere Document din Postgres (Eliberează HASH-ul)
    db.delete(doc)
    db.commit()

    # 4. Ștergere Fișier Fizic
    paths = [
        os.path.join("/app/uploads", filename),
        os.path.join("/app/backend/uploads", filename),
        os.path.join("./uploads", filename)
    ]
    for p in paths:
        if os.path.exists(p):
            try: os.remove(p)
            except: pass
            
    log_event("DOCUMENT_DELETED", user_id=current_user.id, case_id=case_id, details={"filename": filename})
    return {"message": "Purjare completă reușită."}
