import os
import json
import uuid
from collections import defaultdict, deque

import redis
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_forensic_db, SessionLocal
from .. import models
from .auth import get_current_user
from ..services.graph_service import graph_service
from ..services.chat_service import AgenticInvestigator
from ..core.audit import log_event

router = APIRouter(prefix="/cases", tags=["cases"])

r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _check_access(case_id: int, user: models.User, db: Session):
    """ADMIN/MASTER văd tot; ceilalți doar cazurile în care sunt membri."""
    if user.role in ["ADMIN", "MASTER"]:
        return True
    member = db.query(models.CaseMember).filter(
        models.CaseMember.case_id == case_id,
        models.CaseMember.user_id == user.id,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Nu aveți acces la acest dosar.")
    return True


def _doc_ids(db: Session, case_id: int):
    return [d.id for d in db.query(models.Document.id).filter(models.Document.case_id == case_id).all()]


def _build_case_graph(db: Session, case_id: int):
    """Construiește graful (noduri + muchii + adiacență) din SQL.
    Independent de Neo4j, ca să funcționeze chiar dacă sync-ul de graf a eșuat."""
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    case_node_id = f"case_{case_id}"
    nodes = {case_node_id: {"id": case_node_id, "name": case.name if case else f"Dosar {case_id}", "label": "CASE"}}
    links = []
    adjacency = defaultdict(set)

    def add_link(a, b):
        links.append({"source": a, "target": b})
        adjacency[a].add(b)
        adjacency[b].add(a)

    docs = db.query(models.Document).filter(models.Document.case_id == case_id).all()
    doc_node = {}
    for d in docs:
        nid = f"doc_{d.id}"
        doc_node[d.id] = nid
        nodes[nid] = {"id": nid, "name": d.filename, "filename": d.filename, "label": "DOC"}
        add_link(case_node_id, nid)

    # Entități legate de documentele dosarului
    rows = db.execute(text("""
        SELECT l.document_id, e.id, e.official_name, e.entity_type, l.role
        FROM document_entity_links l
        JOIN master_entities e ON e.id = l.entity_id
        WHERE l.document_id = ANY(:ids)
    """), {"ids": _doc_ids(db, case_id) or [-1]}).fetchall()

    for doc_id, ent_id, official_name, entity_type, role in rows:
        if not official_name:
            continue
        nid = f"ent_{ent_id}"
        if nid not in nodes:
            nodes[nid] = {"id": nid, "name": official_name, "label": "ENTITY", "type": entity_type, "role": role}
        if doc_id in doc_node:
            add_link(doc_node[doc_id], nid)

    return list(nodes.values()), links, adjacency


# --------------------------------------------------------------------------- #
# Cases CRUD
# --------------------------------------------------------------------------- #
@router.get("/")
def list_cases(user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    q = db.query(models.Case)
    if user.role not in ["ADMIN", "MASTER"]:
        member_ids = [m.case_id for m in db.query(models.CaseMember).filter(models.CaseMember.user_id == user.id).all()]
        q = q.filter(models.Case.id.in_(member_ids or [-1]))
    cases = q.order_by(models.Case.created_at.desc()).all()
    out = []
    for c in cases:
        cnt = db.query(models.Document).filter(models.Document.case_id == c.id).count()
        out.append({
            "id": c.id, "name": c.name, "description": c.description,
            "status": c.status, "created_at": c.created_at, "document_count": cnt,
        })
    return out


@router.post("/")
def create_case(payload: dict = Body(...), user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    if user.role == "WORKER":
        raise HTTPException(status_code=403, detail="Rol insuficient.")
    c = models.Case(
        name=payload.get("name", "Dosar nou"),
        description=payload.get("description", ""),
        created_by=user.id,
        status="open",
    )
    db.add(c); db.commit(); db.refresh(c)
    db.add(models.CaseMember(case_id=c.id, user_id=user.id, added_by=user.id)); db.commit()
    log_event("CASE_CREATED", user_id=user.id, case_id=c.id, details={"name": c.name})
    return {"id": c.id, "name": c.name}


@router.post("/{case_id}/delete")
def delete_case(case_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    _check_access(case_id, user, db)
    ids = _doc_ids(db, case_id)
    if ids:
        db.execute(text("DELETE FROM document_chunks WHERE document_id = ANY(:ids)"), {"ids": ids})
        db.execute(text("DELETE FROM financial_items WHERE document_id = ANY(:ids)"), {"ids": ids})
        db.execute(text("DELETE FROM document_entity_links WHERE document_id = ANY(:ids)"), {"ids": ids})
    db.query(models.ChatMessage).filter(models.ChatMessage.case_id == case_id).delete()
    db.query(models.Document).filter(models.Document.case_id == case_id).delete()
    db.query(models.CaseMember).filter(models.CaseMember.case_id == case_id).delete()
    db.query(models.Case).filter(models.Case.id == case_id).delete()
    db.commit()
    try:
        if graph_service.driver:
            with graph_service.driver.session() as s:
                s.run("MATCH (c:Case {id:$cid})<-[:PART_OF]-(d:Document) DETACH DELETE d", cid=case_id)
                s.run("MATCH (c:Case {id:$cid}) DETACH DELETE c", cid=case_id)
    except Exception as e:
        print(f"[!] Graf cleanup eroare: {e}")
    log_event("CASE_DELETED", user_id=user.id, case_id=case_id)
    return {"status": "deleted"}


# --------------------------------------------------------------------------- #
# Documents
# --------------------------------------------------------------------------- #
@router.get("/{case_id}/documents")
def list_documents(case_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    _check_access(case_id, user, db)
    docs = db.query(models.Document).filter(models.Document.case_id == case_id).order_by(models.Document.created_at.asc()).all()
    return [{
        "id": d.id, "filename": d.filename, "status": d.status,
        "doc_type": d.doc_type, "ai_summary": d.ai_summary,
        "risk_score": d.risk_score, "created_at": d.created_at,
    } for d in docs]


@router.get("/progress/{doc_id}")
def doc_progress(doc_id: int):
    raw = r.get(f"doc_progress_{doc_id}")
    if not raw:
        return {"status": "UNKNOWN", "percent": 0, "message": "Fără date de progres."}
    try:
        return json.loads(raw)
    except Exception:
        return {"status": "UNKNOWN", "percent": 0, "message": "Progres invalid."}


def _reset_document_data(db: Session, doc_id: int):
    db.execute(text("DELETE FROM document_chunks WHERE document_id = :id"), {"id": doc_id})
    db.execute(text("DELETE FROM financial_items WHERE document_id = :id"), {"id": doc_id})
    db.execute(text("DELETE FROM document_entity_links WHERE document_id = :id"), {"id": doc_id})
    db.commit()
    r.delete(f"doc_progress_{doc_id}")


@router.post("/documents/{doc_id}/pause")
def doc_pause(doc_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    d = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not d: raise HTTPException(404, "Document inexistent.")
    _check_access(d.case_id, user, db)
    d.status = "PAUSED"; db.commit()
    return {"status": "PAUSED"}


@router.post("/documents/{doc_id}/resume")
def doc_resume(doc_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    d = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not d: raise HTTPException(404, "Document inexistent.")
    _check_access(d.case_id, user, db)
    d.status = "QUEUED"; db.commit()
    return {"status": "QUEUED"}


@router.post("/documents/{doc_id}/stop")
def doc_stop(doc_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    d = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not d: raise HTTPException(404, "Document inexistent.")
    _check_access(d.case_id, user, db)
    d.status = "FAILED"; db.commit()
    r.delete(f"doc_progress_{doc_id}")
    return {"status": "STOPPED"}


@router.post("/documents/{doc_id}/retry")
def doc_retry(doc_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    d = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not d: raise HTTPException(404, "Document inexistent.")
    _check_access(d.case_id, user, db)
    _reset_document_data(db, doc_id)
    d.status = "QUEUED"; d.processed = False; db.commit()
    return {"status": "QUEUED"}


@router.post("/documents/{doc_id}/delete")
def doc_delete(doc_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    d = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not d: raise HTTPException(404, "Document inexistent.")
    _check_access(d.case_id, user, db)
    _reset_document_data(db, doc_id)
    db.query(models.Document).filter(models.Document.id == doc_id).delete()
    db.commit()
    return {"status": "deleted"}


# --------------------------------------------------------------------------- #
# Entities / Summary / Graph / Timeline
# --------------------------------------------------------------------------- #
@router.get("/{case_id}/entities")
def list_entities(case_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    _check_access(case_id, user, db)
    rows = db.execute(text("""
        SELECT e.id, e.official_name, e.entity_type, l.role, COUNT(*) AS cnt
        FROM document_entity_links l
        JOIN master_entities e ON e.id = l.entity_id
        WHERE l.document_id = ANY(:ids)
        GROUP BY e.id, e.official_name, e.entity_type, l.role
        ORDER BY cnt DESC
    """), {"ids": _doc_ids(db, case_id) or [-1]}).fetchall()
    return [{
        "id": row[0], "official_name": row[1], "name": row[1],
        "entity_type": row[2], "role": row[3], "count": row[4],
    } for row in rows]


@router.get("/{case_id}/summary")
def case_summary(case_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    """Sinteză rapidă (fără LLM): agregă rezumatele documentelor procesate.
    Endpoint apelat la fiecare 5s de polling, deci NU trebuie să fie costisitor."""
    _check_access(case_id, user, db)
    docs = db.query(models.Document).filter(models.Document.case_id == case_id).all()
    total = len(docs)
    completed = sum(1 for d in docs if d.status == "COMPLETED")
    parts = []
    for d in docs:
        if d.ai_summary:
            parts.append(f"• {d.filename}: {d.ai_summary.strip()}")
    if not parts:
        body = "Niciun document procesat încă. Sinteza va fi disponibilă după finalizarea procesării."
    else:
        body = "\n\n".join(parts)
    header = f"Dosar cu {total} documente ({completed} procesate complet).\n\n"
    return {"summary": header + body, "total": total, "completed": completed}


@router.get("/{case_id}/graph")
def case_graph(case_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    _check_access(case_id, user, db)
    nodes, links, _ = _build_case_graph(db, case_id)
    return {"nodes": nodes, "links": links}


@router.get("/{case_id}/timeline")
def case_timeline(case_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    _check_access(case_id, user, db)
    rows = db.execute(text("""
        SELECT transaction_date, description, doc_filename, amount, currency
        FROM financial_items
        WHERE document_id = ANY(:ids) AND transaction_date IS NOT NULL AND transaction_date <> ''
        ORDER BY transaction_date ASC
        LIMIT 500
    """), {"ids": _doc_ids(db, case_id) or [-1]}).fetchall()
    events = []
    for d, desc, fname, amount, currency in rows:
        title = desc or "Tranzacție"
        if amount:
            title = f"{title} ({amount} {currency or 'RON'})"
        events.append({"date": d, "title": title, "type": "TRANSACTION", "doc_name": fname})
    return events


# --------------------------------------------------------------------------- #
# Graph analytics
# --------------------------------------------------------------------------- #
@router.get("/{case_id}/graph/analytics/leader")
def analytics_leader(case_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    """Degree centrality: scor = numărul de conexiuni per nod."""
    _check_access(case_id, user, db)
    _, _, adjacency = _build_case_graph(db, case_id)
    return {nid: len(neigh) for nid, neigh in adjacency.items()}


@router.get("/{case_id}/graph/analytics/cartel")
def analytics_cartel(case_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    """Detecție de comunități prin componente conexe."""
    _check_access(case_id, user, db)
    nodes, _, adjacency = _build_case_graph(db, case_id)
    community = {}
    comm_id = 0
    for n in nodes:
        nid = n["id"]
        if nid in community:
            continue
        # BFS pentru componenta conexă
        queue = deque([nid])
        community[nid] = comm_id
        while queue:
            cur = queue.popleft()
            for nb in adjacency.get(cur, []):
                if nb not in community:
                    community[nb] = comm_id
                    queue.append(nb)
        comm_id += 1
    return community


@router.get("/{case_id}/graph/analytics/path")
def analytics_path(case_id: int, source_name: str = Query(...), target_name: str = Query(...),
                   user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    """Cel mai scurt traseu (BFS) între două noduri identificate după nume."""
    _check_access(case_id, user, db)
    nodes, _, adjacency = _build_case_graph(db, case_id)

    def find_id(name):
        name = name.strip().lower()
        for n in nodes:
            if name in str(n.get("name", "")).lower():
                return n["id"]
        return None

    src, dst = find_id(source_name), find_id(target_name)
    if not src or not dst:
        return {"nodes": []}

    # BFS
    prev = {src: None}
    queue = deque([src])
    while queue:
        cur = queue.popleft()
        if cur == dst:
            break
        for nb in adjacency.get(cur, []):
            if nb not in prev:
                prev[nb] = cur
                queue.append(nb)

    if dst not in prev:
        return {"nodes": []}
    path = []
    cur = dst
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    return {"nodes": list(reversed(path))}


# --------------------------------------------------------------------------- #
# Chat
# --------------------------------------------------------------------------- #
@router.get("/{case_id}/chat")
def get_chat(case_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    _check_access(case_id, user, db)
    msgs = db.query(models.ChatMessage).filter(models.ChatMessage.case_id == case_id).order_by(models.ChatMessage.created_at.asc()).all()
    return [{
        "id": m.id, "role": m.role, "content": m.content,
        "sql": m.sql, "citations": m.citations or [],
    } for m in msgs]


@router.post("/{case_id}/chat/clear")
def clear_chat(case_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    _check_access(case_id, user, db)
    db.query(models.ChatMessage).filter(models.ChatMessage.case_id == case_id).delete()
    db.commit()
    return {"status": "cleared"}


@router.post("/{case_id}/chat/{msg_id}/delete")
def delete_message(case_id: int, msg_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    _check_access(case_id, user, db)
    db.query(models.ChatMessage).filter(models.ChatMessage.id == msg_id, models.ChatMessage.case_id == case_id).delete()
    db.commit()
    return {"status": "deleted"}


@router.post("/{case_id}/chat/stop")
def stop_chat(case_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    _check_access(case_id, user, db)
    r.set(f"chat_stop_{case_id}", "1", ex=120)
    return {"status": "stopping"}


@router.post("/{case_id}/chat")
def chat(case_id: int, payload: dict = Body(...), user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    _check_access(case_id, user, db)
    question = (payload.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Întrebare goală.")

    # Salvăm întrebarea utilizatorului
    db.add(models.ChatMessage(case_id=case_id, role="user", content=question))
    db.commit()
    r.delete(f"chat_stop_{case_id}")

    def stream():
        agent = AgenticInvestigator(case_id, question)
        trace_logs = []
        final_content = ""
        try:
            for chunk_json in agent.run():
                if r.exists(f"chat_stop_{case_id}"):
                    r.delete(f"chat_stop_{case_id}")
                    stop_evt = json.dumps({"type": "final", "data": "Investigație oprită de utilizator.", "citations": agent.citations})
                    yield stop_evt + "\n"
                    final_content = "Investigație oprită de utilizator."
                    break
                try:
                    evt = json.loads(chunk_json)
                except Exception:
                    continue
                if evt.get("type") == "final":
                    final_content = evt.get("data", "")
                else:
                    trace_logs.append(evt)
                yield chunk_json + "\n"
        except Exception as e:
            err = json.dumps({"type": "error", "data": str(e)})
            yield err + "\n"
        finally:
            # Persistăm răspunsul asistentului cu jurnalul de investigație + citate
            try:
                with SessionLocal() as sdb:
                    sdb.add(models.ChatMessage(
                        case_id=case_id,
                        role="assistant",
                        content=final_content,
                        sql=json.dumps(trace_logs, ensure_ascii=False),
                        citations=agent.citations,
                    ))
                    sdb.commit()
            except Exception as e:
                print(f"[!] Eroare salvare mesaj asistent: {e}")

    return StreamingResponse(stream(), media_type="application/x-ndjson")


# --------------------------------------------------------------------------- #
# Audit report (PDF)
# --------------------------------------------------------------------------- #
@router.get("/{case_id}/audit-report")
def audit_report(case_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_forensic_db)):
    _check_access(case_id, user, db)
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(404, "Dosar inexistent.")
    docs = db.query(models.Document).filter(models.Document.case_id == case_id).all()
    if not docs:
        raise HTTPException(400, "Dosarul nu conține documente procesate.")

    entities = list_entities(case_id, user, db)

    try:
        from fpdf import FPDF
    except Exception:
        raise HTTPException(500, "Generatorul PDF (fpdf2) nu este disponibil.")

    def clean(s):
        return str(s or "").encode("latin-1", "replace").decode("latin-1")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, clean(f"Raport Audit - {case.name}"), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, clean(f"Dosar #{case.id} | {len(docs)} documente"), ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "Documente", ln=True)
    pdf.set_font("Helvetica", "", 9)
    for d in docs:
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(0, 6, clean(f"{d.filename}  [{d.status}]"))
        if d.ai_summary:
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, clean(d.ai_summary))
        pdf.ln(1)

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, "Entitati identificate", ln=True)
    pdf.set_font("Helvetica", "", 9)
    for e in entities[:100]:
        pdf.multi_cell(0, 5, clean(f"- {e['official_name']} ({e['entity_type'] or 'N/A'}) | rol: {e['role'] or 'N/A'} | apariții: {e['count']}"))

    out = pdf.output()
    pdf_bytes = bytes(out) if not isinstance(out, (bytes, bytearray)) else out
    log_event("AUDIT_REPORT_GENERATED", user_id=user.id, case_id=case_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Raport_Audit_Dosar_{case_id}.pdf"},
    )
