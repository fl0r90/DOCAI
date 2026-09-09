# TEST_SYNC_12345
import os
import requests
import json
import re
import time
from sqlalchemy import text, or_, and_
from ..database import engine, SessionLocal
from ..core.config import get_llm_config, get_active_model_name
from ..models import DocumentChunk, Document, ChatMessage, Case
from .. import models
from .graph_service import GraphService
from .llm_client import UnifiedLLMClient

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434")
VLLM_URL = os.getenv("VLLM_URL", "http://v2-vllm:8000/v1")

ROMANIAN_MONTHS = {
    1: ["ianuarie", "ian"],
    2: ["februarie", "feb"],
    3: ["martie", "mar"],
    4: ["aprilie", "apr"],
    5: ["mai"],
    6: ["iunie", "iun"],
    7: ["iulie", "iul"],
    8: ["august", "aug"],
    9: ["septembrie", "sept", "sep"],
    10: ["octombrie", "oct"],
    11: ["noiembrie", "nov"],
    12: ["decembrie", "dec"]
}

def get_date_variants(text: str) -> list:
    """
    Extracts date patterns (e.g. 17.01.2025, 17-01-2025, 17/01/2025, 17 ianuarie 2025)
    and generates all common variants (dots, hyphens, slashes, Romanian text months, ISO format).
    """
    if not text:
        return []
    variants = set()
    # 1. DD[./-]MM[./-]YYYY
    pattern_dmy = re.findall(r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b', text)
    for d_str, m_str, y_str in pattern_dmy:
        try:
            d = int(d_str)
            m = int(m_str)
            y = int(y_str)
            if y < 100:
                y += 2000
            if 1 <= d <= 31 and 1 <= m <= 12:
                variants.add(f"{d:02d}-{m:02d}-{y}")
                variants.add(f"{d:02d}.{m:02d}.{y}")
                variants.add(f"{d:02d}/{m:02d}/{y}")
                variants.add(f"{d}-{m}-{y}")
                variants.add(f"{d}.{m}.{y}")
                variants.add(f"{d}/{m}/{y}")
                variants.add(f"{y}-{m:02d}-{d:02d}")
                variants.add(f"{y}.{m:02d}.{d:02d}")
                for m_name in ROMANIAN_MONTHS.get(m, []):
                    variants.add(f"{d} {m_name} {y}")
                    variants.add(f"{d:02d} {m_name} {y}")
        except Exception:
            pass

    # 2. Match text format: DD <month_name> YYYY
    pattern_text = re.findall(r'\b(\d{1,2})\s+([a-zA-ZăâîșțĂÂÎȘȚ]+)\s+(\d{4})\b', text, re.IGNORECASE)
    for d_str, m_name, y_str in pattern_text:
        m_lower = m_name.lower()
        matched_m = None
        for m_idx, m_names in ROMANIAN_MONTHS.items():
            if any(m_lower.startswith(mn) for mn in m_names):
                matched_m = m_idx
                break
        if matched_m:
            try:
                d = int(d_str)
                y = int(y_str)
                if 1 <= d <= 31:
                    variants.add(f"{d:02d}-{matched_m:02d}-{y}")
                    variants.add(f"{d:02d}.{matched_m:02d}.{y}")
                    variants.add(f"{d:02d}/{matched_m:02d}/{y}")
                    variants.add(f"{d}-{matched_m}-{y}")
                    variants.add(f"{d}.{matched_m}.{y}")
                    variants.add(f"{y}-{matched_m:02d}-{d:02d}")
            except Exception:
                pass

    return list(variants)

def decompose_question(q: str) -> list:
    """Decomposes a complex multi-part user question into atomic targets (sub-questions)."""
    targets = []
    if ":" in q:
        parts = q.split(":", 1)
        clauses = re.split(r"[\?,;]|\b(?:si|și|precum și)\b", parts[1])
        for c in clauses:
            c = c.strip()
            if len(c) > 5 and any(w in c.lower() for w in ["care", "ce", "cat", "cât", "cine", "unde", "cand", "când", "amprenta", "adrese", "volum", "suma", "data", "nume", "cati", "câți"]):
                targets.append(c)
            elif len(c) > 10:
                targets.append(c)
    
    if not targets:
        clauses = [c.strip() for c in q.split("?") if c.strip()]
        if len(clauses) > 1:
            targets = clauses

    if not targets and any(w in q.lower() for w in [" și ", " si ", " precum și "]):
        clauses = re.split(r"\b(?:si|și|precum și)\b", q)
        if len(clauses) > 1 and all(len(c.strip()) > 8 for c in clauses):
            q_words = ["cine", "ce", "cat", "cât", "care", "cand", "când", "unde", "de ce", "cum"]
            if any(any(qw in c.lower() for qw in q_words) for c in clauses[1:]):
                targets = [c.strip() for c in clauses if c.strip()]

    if not targets:
        targets = [q.strip()]
        
    return targets

class AgenticInvestigator:
    def __init__(self, case_id: int, user_question: str):
        self.case_id = case_id
        self.user_question = user_question
        self.active_model = get_active_model_name()
        self.citations = []
        self.graph = GraphService()
        self.injected_evidence = ""
        self.history = []
        self.sub_targets = decompose_question(self.user_question)
        self.scratchpad = {
            i: {"target": t, "status": "PENDING", "confidence": "NONE", "fact": "", "citations": []}
            for i, t in enumerate(self.sub_targets, 1)
        }
        self._load_history()
        self._pre_process_query()

    def _render_scratchpad(self) -> str:
        lines = ["=== PROGRESSIVE WORKING MEMORY (TEMPORARY SCRATCHPAD) ==="]
        for i, data in self.scratchpad.items():
            status_str = f"[{data['status']} | Confidence: {data['confidence']}]"
            fact_str = f" -> Evidence: {data['fact']} (Ref: {data['citations']})" if data['fact'] else ""
            lines.append(f"Target {i}: {data['target']} | {status_str}{fact_str}")
        lines.append("=========================================================")
        return "\n".join(lines)

    def _load_history(self):
        """Loads last 4 messages (2 turns) for context window, excluding the current question if already saved."""
        with SessionLocal() as db:
            past_msgs = db.query(ChatMessage).filter(ChatMessage.case_id == self.case_id).order_by(ChatMessage.created_at.desc()).limit(7).all()
            # If the most recent message in DB is the current user question (saved by cases.py before launching), skip it
            if past_msgs and past_msgs[0].role == "user" and past_msgs[0].content.strip() == self.user_question.strip():
                past_msgs = past_msgs[1:5]
            else:
                past_msgs = past_msgs[:4]

            # Reverse to get chronological order
            for m in reversed(past_msgs):
                # We strip the investigation logs from history to keep context clean
                clean_content = m.content.split("**LOG INVESTIGATIE:**")[0].strip()
                # Truncate past long assistant messages to prevent prompt context pollution
                if m.role == "assistant" and len(clean_content) > 1200:
                    clean_content = clean_content[:1200] + "\n[... Conținut anterior trunchiat pentru economisire context ...]"
                if clean_content:
                    self.history.append({"role": m.role, "content": clean_content})

    def _pre_process_query(self):
        """Initial check for obvious entities and dates to seed the prompt."""
        with SessionLocal() as db:
            doc_ids = [d.id for d in db.query(Document).filter(Document.case_id == self.case_id).all()]
            if not doc_ids: return

            # Extract temporal anchors (Years, Months, Dates)
            months = ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"]
            found_months = [m for m in months if m in self.user_question.lower()]
            found_years = re.findall(r'20\d{2}', self.user_question)
            found_dates = get_date_variants(self.user_question)
            
            # Extract obvious entities (ALL CAPS)
            anchors = re.findall(r'[A-Z]{3,30}', self.user_question)
            
            if anchors or found_months or found_years or found_dates:
                self.injected_evidence = "--- PRELIMINARY CONTEXT ---\n"
                self.injected_evidence += f"Detected Subject(s): {', '.join(anchors) if anchors else 'None'}\n"
                self.injected_evidence += f"Detected Time Constraints: {' '.join(found_months)} {' '.join(found_years)}\n"
                if found_dates:
                    self.injected_evidence += f"Detected Explicit Date Variations to Search: {', '.join(found_dates[:6])}\n"
                
        # Agnostic Intent Detection
        q_lower = self.user_question.lower()
        if any(k in q_lower for k in ["cati", "câți", "cate", "câte", "total", "suma", "listă completă", "lista completa"]):
            self.injected_evidence += "CRITICAL: The user is asking for a QUANTITATIVE answer or a TOTAL COUNT. You MUST use SEARCH_STRUCTURED_DATA to get accurate counts from the database tables. Do NOT rely on individual text fragments for totals.\n"
        elif any(k in q_lower for k in ["plata", "incasare", "suma", "ron", "usd", "achizitie", "pret", "valoare", "cost"]):
            self.injected_evidence += "Suggested Intent: TABULAR / FINANCIAL -> Use SEARCH_STRUCTURED_DATA for hard figures.\n"
        else:
            self.injected_evidence += "Suggested Intent: CONTEXTUAL / TEXTUAL -> Use SEARCH_TEXT for document details.\n"
                
        if anchors:
            self.injected_evidence += "Relational Check: Entities detected. EXPLORE_GRAPH may provide links.\n"

        if self.scratchpad:
            self.injected_evidence += "\n" + self._render_scratchpad() + "\n"
        
        self.injected_evidence += "Use the specialized tools below to find exact records.\n"

    def tool_search_text(self, query: str, semantic_intent: str = ""):
        """Tool 1: Hybrid Search (Lexical + Vector + Date-Aware) in document chunks."""
        with SessionLocal() as db:
            all_docs = db.query(Document).filter(Document.case_id == self.case_id).all()
            doc_ids = [d.id for d in all_docs]
            if not doc_ids: return "No documents in this case."
            
            # Apply semantic intent filter (search in doc_type, filename OR dynamic_attributes)
            if semantic_intent:
                intent_ids = []
                si_lower = semantic_intent.lower()
                for d in all_docs:
                    matched = False
                    if d.doc_type and si_lower in d.doc_type.lower():
                        matched = True
                    elif si_lower in d.filename.lower():
                        matched = True
                    elif d.doc_metadata and isinstance(d.doc_metadata, dict):
                        dyn = d.doc_metadata.get("dynamic_attributes", {})
                        if isinstance(dyn, dict):
                            for k, v in dyn.items():
                                if si_lower in str(k).lower() or si_lower in str(v).lower():
                                    matched = True
                                    break
                    if matched:
                        intent_ids.append(d.id)
                
                if intent_ids:
                    doc_ids = intent_ids
                else:
                    # Fallback: warn but continue search in all documents
                    intent_warning = f"Note: No documents found matching type/name '{semantic_intent}'. Searching all docs instead.\n"
            else:
                intent_warning = ""
            
            # Extract date variants from both the query AND the user question
            date_variants = get_date_variants(query)
            if not date_variants and self.user_question:
                date_variants = get_date_variants(self.user_question)

            words = [w.strip() for w in re.findall(r'\b\w{2,}\b', query) if len(w) >= 2]
            if not words and not date_variants:
                return "No valid keywords or dates for text search."

            # 1. Date Exact Search (fetch chunks matching any date variant directly)
            date_res = []
            if date_variants:
                date_conditions = [DocumentChunk.content.ilike(f"%{dv}%") for dv in date_variants]
                date_res = db.query(DocumentChunk)\
                    .filter(and_(DocumentChunk.document_id.in_(doc_ids), or_(*date_conditions)))\
                    .limit(30).all()

            # 2. Semantic Search (Vector)
            query_embedding = None
            try:
                from .embedding_service import EmbeddingService
                query_embedding = EmbeddingService.get_embedding(query)
            except Exception as e:
                print(f"[!] Embedding Error in Hybrid Search: {e}")

            vector_res = []
            if query_embedding:
                try:
                    # Top 20 by semantic similarity
                    vector_res = db.query(DocumentChunk)\
                        .filter(DocumentChunk.document_id.in_(doc_ids))\
                        .order_by(DocumentChunk.embedding.l2_distance(query_embedding))\
                        .limit(20).all()
                except Exception as e:
                    db.rollback()
                    print(f"[!] pgvector search error: {e}")

            # 3. Lexical Search (Exact Keyword Match via ILIKE)
            lexical_res = []
            lex_words = [w for w in words if len(w) >= 3]
            if lex_words:
                conditions = [DocumentChunk.content.ilike(f"%{w}%") for w in lex_words]
                lexical_res = db.query(DocumentChunk)\
                    .filter(and_(DocumentChunk.document_id.in_(doc_ids), or_(*conditions)))\
                    .limit(30).all()

            # 4. Merge & Deduplicate (date_res prioritized first)
            seen_ids = set()
            merged_results = []
            for r in date_res + vector_res + lexical_res:
                if r.id not in seen_ids:
                    seen_ids.add(r.id)
                    merged_results.append(r)

            if not merged_results: return "No text fragments found."

            # 5. Neural Reranking via SentenceTransformers (with Rule-based Fallback)
            scored_res = []
            try:
                from .rerank_service import RerankService
                reranker = RerankService.get_instance()
                # Rerank query with candidates
                scored_res = reranker.rerank(query, merged_results, top_k=20)
                print(f"[+] Successfully reranked {len(merged_results)} candidates using cross-encoder.")
                if date_variants:
                    boosted = []
                    for s, r in scored_res:
                        boost = 0.0
                        c_low = r.content.lower()
                        for dv in date_variants:
                            if dv.lower() in c_low:
                                boost += 5.0
                                break
                        boosted.append((s + boost, r))
                    boosted.sort(key=lambda x: x[0], reverse=True)
                    scored_res = boosted
            except Exception as e:
                print(f"[!] Reranker failed or not loaded, falling back to keyword scoring: {e}")
                # Fallback rule-based scorer
                def calculate_score(res):
                    score = 0
                    content_raw = res.content
                    content_lower = content_raw.lower()
                    doc = db.query(Document).filter(Document.id == res.document_id).first()
                    filename_lower = doc.filename.lower() if doc else ""
                    entities = re.findall(r'\b[A-Z]{3,}\b', query)
                    for w in words:
                        w_low = w.lower()
                        if w_low in content_lower: score += 1
                        if w_low in filename_lower: score += 5
                    for ent in entities:
                        if ent in content_raw: score += 20
                        if ent.lower() in filename_lower: score += 50
                    for dv in date_variants:
                        if dv.lower() in content_lower: score += 30
                    return score

                scored_res = sorted(
                    [(calculate_score(r), r) for r in merged_results], 
                    key=lambda x: x[0], 
                    reverse=True
                )

            # 5. Document-Level Context Assembly (Limit 4096 characters per document)
            # Grupează rezultatele pe documente pentru a elimina duplicările și a oferi context complet până la 4096 caractere per document.
            DOC_CONTEXT_LIMIT = 4096
            MAX_DOCS_RETURNED = 8
            MAX_TOTAL_CHARS = 25000

            doc_matches = {}  # doc_id -> list of (score, chunk)
            top_score = scored_res[0][0] if scored_res else 0.0
            min_score_threshold = 0.03 if top_score > 0.2 else -999.0

            for s, r in scored_res:
                if s < min_score_threshold and len(doc_matches) >= 3:
                    continue
                if r.document_id not in doc_matches:
                    doc_matches[r.document_id] = []
                doc_matches[r.document_id].append((s, r))

            final_res = []
            total_chars_accumulated = 0

            for doc_id, chunk_list in list(doc_matches.items())[:MAX_DOCS_RETURNED]:
                if total_chars_accumulated >= MAX_TOTAL_CHARS:
                    break

                best_score, best_chunk = chunk_list[0]
                doc_obj = db.query(Document).filter(Document.id == doc_id).first()
                if not doc_obj:
                    continue

                page_num = getattr(best_chunk, 'page_number', 1) or 1
                doc_context = ""

                if doc_obj.raw_text:
                    raw = doc_obj.raw_text.strip()
                    if len(raw) <= DOC_CONTEXT_LIMIT:
                        # Documentul complet încape în limita de 4096 caractere (fidelitate maximă)
                        doc_context = raw
                    else:
                        # Fereastră centrată de 4096 caractere în jurul celui mai relevant fragment
                        needle = re.sub(r'^\[Doc:[^\]]*\]\s*', '', best_chunk.content).strip()
                        search_sub = needle[:min(60, len(needle))].strip() if needle else ""
                        pos = raw.find(search_sub) if search_sub else -1

                        if pos == -1 and len(needle) > 80:
                            pos = raw.find(needle[20:70])

                        if pos != -1:
                            half = DOC_CONTEXT_LIMIT // 2
                            start = max(0, pos - half)
                            end = min(len(raw), start + DOC_CONTEXT_LIMIT)
                            if end - start < DOC_CONTEXT_LIMIT and start > 0:
                                start = max(0, end - DOC_CONTEXT_LIMIT)
                        else:
                            all_doc_chunks = db.query(DocumentChunk.id).filter(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.id).all()
                            c_ids = [c[0] for c in all_doc_chunks]
                            idx = c_ids.index(best_chunk.id) if best_chunk.id in c_ids else 0
                            ratio = idx / max(1, len(c_ids))
                            pos = int(ratio * len(raw))
                            half = DOC_CONTEXT_LIMIT // 2
                            start = max(0, pos - half)
                            end = min(len(raw), start + DOC_CONTEXT_LIMIT)
                            if end - start < DOC_CONTEXT_LIMIT and start > 0:
                                start = max(0, end - DOC_CONTEXT_LIMIT)

                        prefix = "[... Fragment anterior omis ...]\n" if start > 0 else ""
                        suffix = "\n[... Fragment ulterior omis ...]" if end < len(raw) else ""
                        doc_context = prefix + raw[start:end] + suffix
                else:
                    # Fallback dacă raw_text lipsește
                    all_chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.page_number, DocumentChunk.id).all()
                    accum = []
                    cur_len = 0
                    for c in all_chunks:
                        if cur_len + len(c.content) > DOC_CONTEXT_LIMIT:
                            break
                        accum.append(c.content)
                        cur_len += len(c.content)
                    doc_context = "\n\n".join(accum) if accum else best_chunk.content[:DOC_CONTEXT_LIMIT]

                if not doc_context.strip():
                    continue

                total_chars_accumulated += len(doc_context)
                citation_id = len(self.citations) + 1

                self.citations.append({
                    "id": citation_id,
                    "doc_id": doc_obj.id,
                    "page": page_num,
                    "content": doc_context[:300],
                    "filename": doc_obj.filename if doc_obj else "unknown",
                    "spatial": getattr(best_chunk, "spatial", "") or ""
                })

                doc_type_tag = f" | {doc_obj.doc_type}" if (doc_obj and doc_obj.doc_type) else ""
                dyn_meta = ""
                if doc_obj.doc_metadata and isinstance(doc_obj.doc_metadata, dict):
                    dyn = doc_obj.doc_metadata.get("dynamic_attributes")
                    if dyn and isinstance(dyn, dict):
                        dyn_strs = [f"{k}: {v}" for k, v in dyn.items() if v and not isinstance(v, (dict, list))]
                        if dyn_strs:
                            dyn_meta = f" | {', '.join(dyn_strs[:5])}"

                header = f"[REF {citation_id} - {doc_obj.filename if doc_obj else 'Doc'}{doc_type_tag}{dyn_meta}, Pagina {page_num}]"
                final_res.append(f"{header}:\n{doc_context}")

            graph_context = ""
            entities_to_query = re.findall(r'\b[A-Z]{3,}\b', query) + [w for w in words if len(w) >= 4]
            if entities_to_query:
                subgraph_info = self.graph.get_entity_subgraph(entities_to_query, limit=10)
                if subgraph_info:
                    graph_context = f"\n\n--- RELATIONAL GRAPH CONTEXT (Neo4j Connections) ---\n{subgraph_info}"

            return "\n\n".join(final_res) + graph_context

    def tool_fetch_full_document(self, doc_id: int, focus_terms: str = ""):
        """Tool: Retrieve complete full-text (up to 4096 characters or expanded context window) of a specific document when confidence is MEDIUM."""
        with SessionLocal() as db:
            doc_obj = db.query(Document).filter(Document.id == doc_id).first()
            if not doc_obj:
                return f"Document ID {doc_id} not found."
            
            citation_id = len(self.citations) + 1
            raw = doc_obj.raw_text.strip() if doc_obj.raw_text else ""
            if not raw:
                chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.page_number, DocumentChunk.id).all()
                raw = "\n\n".join([c.content for c in chunks])
            
            # If document fits in 4096, return it completely; otherwise center on focus_terms
            DOC_CONTEXT_LIMIT = 4096
            if len(raw) <= DOC_CONTEXT_LIMIT or not focus_terms:
                doc_context = raw[:DOC_CONTEXT_LIMIT]
            else:
                words = [w.strip() for w in re.findall(r'\b\w{3,}\b', focus_terms)]
                pos = -1
                for w in words:
                    pos = raw.lower().find(w.lower())
                    if pos != -1: break
                if pos != -1:
                    start = max(0, pos - (DOC_CONTEXT_LIMIT // 2))
                    end = min(len(raw), start + DOC_CONTEXT_LIMIT)
                    if end - start < DOC_CONTEXT_LIMIT and start > 0:
                        start = max(0, end - DOC_CONTEXT_LIMIT)
                    prefix = "[... Fragment anterior omis ...]\n" if start > 0 else ""
                    suffix = "\n[... Fragment ulterior omis ...]" if end < len(raw) else ""
                    doc_context = prefix + raw[start:end] + suffix
                else:
                    doc_context = raw[:DOC_CONTEXT_LIMIT]
            
            self.citations.append({
                "id": citation_id,
                "doc_id": doc_obj.id,
                "page": 1,
                "content": doc_context[:300],
                "filename": doc_obj.filename if doc_obj else f"Doc_{doc_id}",
                "spatial": ""
            })
            
            doc_type_tag = f" | {doc_obj.doc_type}" if doc_obj.doc_type else ""
            dyn_meta = ""
            if doc_obj.doc_metadata and isinstance(doc_obj.doc_metadata, dict):
                dyn = doc_obj.doc_metadata.get("dynamic_attributes")
                if dyn and isinstance(dyn, dict):
                    dyn_strs = [f"{k}: {v}" for k, v in dyn.items() if v and not isinstance(v, (dict, list))]
                    if dyn_strs:
                        dyn_meta = f" | {', '.join(dyn_strs[:5])}"
            
            header = f"[REF {citation_id} - FULL DOC: {doc_obj.filename}{doc_type_tag}{dyn_meta}, Pagina 1]"
            return f"{header}:\n{doc_context}"

    def tool_search_transactions(self, subject: str, date_filter: str = "", match_pattern: str = "", aggregate: bool = False, limit: int = 100):
        """Tool 2: Structured search with AGNOSTIC aggregation capability."""
        limit = min(int(limit), 100)
        with SessionLocal() as db:
            doc_ids = [d.id for d in db.query(Document).filter(Document.case_id == self.case_id).all()]
            if not doc_ids: return "No documents in this case."
            
            # AGNOSTIC AGGREGATION: If requested, parse Markdown tables directly
            if aggregate:
                unique_rows = set()
                pattern_variants = get_date_variants(match_pattern) if match_pattern else []
                if match_pattern and not pattern_variants:
                    pattern_variants = [match_pattern.lower()]
                else:
                    pattern_variants = [v.lower() for v in pattern_variants]
                
                subject_terms = [w.strip() for w in re.findall(r'\w{3,}', subject) if len(w) >= 3]
                chunk_filter = [DocumentChunk.content.ilike(f"%{subject}%")]
                if subject_terms:
                    chunk_filter.extend([DocumentChunk.content.ilike(f"%{t}%") for t in subject_terms])
                if pattern_variants:
                    chunk_filter.extend([DocumentChunk.content.ilike(f"%{pv}%") for pv in pattern_variants])

                chunks = db.query(DocumentChunk).filter(
                    DocumentChunk.document_id.in_(doc_ids),
                    or_(*chunk_filter)
                ).all()

                for c in chunks:
                    c_lower = c.content.lower()
                    chunk_matches_pattern = True
                    if pattern_variants:
                        chunk_matches_pattern = any(pv in c_lower for pv in pattern_variants)

                    for line in c.content.split('\n'):
                        if "|" in line:
                            is_subject_match = False
                            if subject.lower() in line.lower() or any(t.lower() in line.lower() for t in subject_terms):
                                is_subject_match = True
                            elif subject.lower() in c_lower and subject.lower() not in ["prezent", "absent"]:
                                is_subject_match = True
                                
                            if is_subject_match:
                                line_matches_pattern = True
                                if pattern_variants:
                                    line_matches_pattern = any(pv in line.lower() for pv in pattern_variants) or chunk_matches_pattern

                                if line_matches_pattern:
                                    if not any(hdr in line.lower() for hdr in ["nume si prenume", "email", "status", "---"]):
                                        clean_line = "|".join([col.strip() for col in line.split("|") if col.strip()])
                                        if clean_line: unique_rows.add(clean_line)
                
                output = f"AGNOSTIC AGGREGATION RESULT FOR '{subject}':\n"
                output += f"TOTAL UNIQUE RECORDS: {len(unique_rows)}\n"
                output += f"UNIQUE RECORDS FOUND (showing first {limit}):\n"
                for row in sorted(list(unique_rows))[:limit]:
                    output += f"- {row}\n"
                if len(unique_rows) > limit:
                    output += f"... and {len(unique_rows) - limit} more unique records.\n"
                return output

            # [Rest of the existing search logic...]
            search_terms = [w.strip() for w in re.findall(r'\w{3,}', subject) if len(w) >= 3]
            if not search_terms and subject: search_terms = [subject]

            output = ""
            
            # --- 1. CĂUTARE ÎN DOCUMENT SUMMARY (NOU) ---
            try:
                doc_query = """
                    SELECT doc_type, COUNT(*) as count, STRING_AGG(DISTINCT filename, ', ' ORDER BY filename) as examples
                    FROM documents
                    WHERE id = ANY(:ids)
                """
                d_params = {"ids": doc_ids}
                if search_terms:
                    d_conditions = []
                    for i, term in enumerate(search_terms):
                        key = f"dterm_{i}"
                        d_conditions.append(f"filename ILIKE :{key} OR doc_type ILIKE :{key}")
                        d_params[key] = f"%{term}%"
                    doc_query += f" AND ({' OR '.join(d_conditions)})"
                
                doc_query += " GROUP BY doc_type ORDER BY count DESC"
                d_res = db.execute(text(doc_query), d_params).fetchall()
                
                if d_res:
                    output += f"--- DOCUMENT SUMMARY (Files in Case) ---\n"
                    for r in d_res:
                        doc_type_label = r[0] if r[0] else "Uncategorized"
                        output += f"- Type: {doc_type_label} | Total: {r[1]} files\n"
                        output += f"  Files: {r[2][:500]}...\n"
                    output += "\n"
            except Exception as e:
                output += f"Document summary error: {e}\n"

            # --- 2. CĂUTARE ÎN ENTITĂȚI ȘI ROLURI (EXISTENT) ---
            try:
                entity_query = """
                    SELECT e.official_name, l.role, COUNT(*) as count
                    FROM master_entities e
                    JOIN document_entity_links l ON e.id = l.entity_id
                    WHERE l.document_id = ANY(:ids)
                """
                e_params = {"ids": doc_ids}
                if search_terms:
                    e_conditions = []
                    for i, term in enumerate(search_terms):
                        key = f"eterm_{i}"
                        e_conditions.append(f"e.official_name ILIKE :{key}")
                        e_params[key] = f"%{term}%"
                    entity_query += f" AND ({' OR '.join(e_conditions)})"
                
                entity_query += " GROUP BY e.official_name, l.role ORDER BY count DESC"
                e_res = db.execute(text(entity_query), e_params).fetchall()
                
                if e_res:
                    output += f"--- ENTITY SUMMARY (Found {len(e_res)} unique roles) ---\n"
                    for r in e_res:
                        output += f"- Entity: {r[0]} | Role: {r[1]} | Total Occurrences: {r[2]}\n"
                    output += "\n"
            except Exception as e:
                output += f"Entity search error: {e}\n"

            # --- 2. CĂUTARE ÎN TRANZACȚII FINANCIARE (EXISTENT) ---
            query_str = "SELECT transaction_date, description, amount, currency, doc_filename FROM financial_items WHERE document_id = ANY(:ids)"
            params = {"ids": doc_ids}
            # ... restul logicii de tranzacții rămâne la fel ...

            if search_terms:
                # Create a group of ILIKE conditions
                term_conditions = []
                for i, term in enumerate(search_terms):
                    key = f"term_{i}"
                    term_conditions.append(f"description ILIKE :{key}")
                    params[key] = f"%{term}%"
                query_str += f" AND ({' OR '.join(term_conditions)})"

            if date_filter:
                # Robust date handling
                # If range like "01.02 to 28.02", extract month/year
                month_year = re.search(r'(\d{2}\.20\d{2})', date_filter)
                if month_year:
                    # Search by month.year (e.g. .02.2026)
                    target = month_year.group(1)
                    if not target.startswith('.'): target = "." + target
                    query_str += " AND (transaction_date LIKE :d_filter OR description LIKE :d_filter)"
                    params["d_filter"] = f"%{target}%"
                else:
                    # Fallback to literal digits
                    date_digits = "".join(re.findall(r'\d+', date_filter))
                    if len(date_digits) >= 2:
                        query_str += " AND (transaction_date LIKE :d_filter OR description LIKE :d_filter)"
                        params["d_filter"] = f"%{date_filter.strip()}%"
                
                query_str += " ORDER BY ABS(amount) DESC LIMIT 50"
            else:
                query_str += " ORDER BY ABS(amount) DESC LIMIT 50"
            
            try:
                res = db.execute(text(query_str), params).fetchall()
                
                # FALLBACK: If no results with date, try without date if subject exists
                if not res and date_filter and search_terms:
                    query_fallback = "SELECT transaction_date, description, amount, currency, doc_filename FROM financial_items WHERE document_id = ANY(:ids)"
                    fallback_params = {"ids": doc_ids}
                    term_conditions = []
                    for i, term in enumerate(search_terms):
                        key = f"term_{i}"
                        term_conditions.append(f"description ILIKE :{key}")
                        fallback_params[key] = f"%{term}%"
                    query_fallback += f" AND ({' OR '.join(term_conditions)}) ORDER BY ABS(amount) DESC LIMIT 20"
                    res = db.execute(text(query_fallback), fallback_params).fetchall()
                    if res:
                        output = f"--- NO RESULTS FOR DATE '{date_filter}', SHOWING ALL RECORDS FOR '{subject}' ---\n"
                    else:
                        return f"No transactions found for '{subject}' in '{date_filter}' or any other date."
                elif not res:
                    # FALLBACK to AGNOSTIC AGGREGATION if no transactions found
                    # This helps in cases (like Case 6) where only tabular attendance data is available
                    unique_rows = set()
                    pattern_variants = get_date_variants(match_pattern or date_filter)
                    if (match_pattern or date_filter) and not pattern_variants:
                        pattern_variants = [(match_pattern or date_filter).lower()]
                    else:
                        pattern_variants = [v.lower() for v in pattern_variants]
                    
                    chunk_filter = [DocumentChunk.content.ilike(f"%{subject}%")]
                    if search_terms:
                        chunk_filter.extend([DocumentChunk.content.ilike(f"%{t}%") for t in search_terms])
                    if pattern_variants:
                        chunk_filter.extend([DocumentChunk.content.ilike(f"%{pv}%") for pv in pattern_variants])

                    chunks = db.query(DocumentChunk).filter(
                        DocumentChunk.document_id.in_(doc_ids),
                        or_(*chunk_filter)
                    ).all()

                    if chunks:
                        for c in chunks:
                            c_lower = c.content.lower()
                            chunk_matches_pattern = True
                            if pattern_variants:
                                chunk_matches_pattern = any(pv in c_lower for pv in pattern_variants)

                            for line in c.content.split('\n'):
                                if "|" in line:
                                    is_subject_match = False
                                    if subject.lower() in line.lower() or any(t.lower() in line.lower() for t in search_terms):
                                        is_subject_match = True
                                    elif subject.lower() in c_lower and subject.lower() not in ["prezent", "absent"]:
                                        is_subject_match = True
                                        
                                    if is_subject_match:
                                        line_matches_pattern = True
                                        if pattern_variants:
                                            line_matches_pattern = any(pv in line.lower() for pv in pattern_variants) or chunk_matches_pattern

                                        if line_matches_pattern:
                                            if not any(hdr in line.lower() for hdr in ["nume si prenume", "email", "status", "---"]):
                                                clean_line = "|".join([col.strip() for col in line.split("|") if col.strip()])
                                                if clean_line: unique_rows.add(clean_line)
                        if unique_rows:
                            output = f"--- NO TRANSACTIONS FOUND. FALLBACK AGNOSTIC AGGREGATION RESULT FOR '{subject}':\n"
                            output += f"TOTAL UNIQUE RECORDS: {len(unique_rows)}\n"
                            output += f"UNIQUE RECORDS FOUND (showing first {limit}):\n"
                            for row in sorted(list(unique_rows))[:limit]:
                                output += f"- {row}\n"
                            if len(unique_rows) > limit:
                                output += f"... and {len(unique_rows) - limit} more unique records.\n"
                            return output
                    return f"No transactions or tabular records found for '{subject}' in '{date_filter}'."
                else:
                    output = f"--- FOUND {len(res)} RECORDS (Verified SQL Data) ---\n"
                for r in res:
                    citation_id = len(self.citations) + 1
                    date_val = r[0] if r[0] and r[0] != "N/A" else "Annual/Period"
                    content_str = f"Tranzacție: {r[1]} | Sumă: {r[2]} {r[3]} | Data: {date_val}"
                    
                    # Înregistrăm citatul
                    self.citations.append({
                        "id": citation_id,
                        "doc_id": "SQL_DB", # Marcăm sursa ca fiind baza de date
                        "page": 0,
                        "content": content_str,
                        "filename": r[4] # doc_filename
                    })
                    
                    output += f"[REF {citation_id}] Type: {date_val} | Amount: {r[2]} {r[3]} | Desc: {r[1]}\n"
                
                graph_context = ""
                if subject:
                    subgraph_info = self.graph.get_entity_subgraph([subject], limit=10)
                    if subgraph_info:
                        graph_context = f"\n\n--- RELATIONAL GRAPH CONTEXT (Neo4j Connections) ---\n{subgraph_info}"
                return output + graph_context
            except Exception as e:
                return f"Transaction search error: {e}"

    def tool_explore_graph(self, entity_name: str):
        """Tool 3: Neo4j relationship exploration."""
        if not self.graph: return "Graph service unavailable."
        # Use existing query_relationships but targeted at a single entity
        result = self.graph.query_relationships([entity_name])
        return result if result else f"No graph relationships found for '{entity_name}'."

    def tool_timeline(self, entity_name: str):
        """Tool 5: Chronological event tracking for an entity."""
        with SessionLocal() as db:
            # Search for the entity in transactions
            tx_res = db.execute(text(
                "SELECT transaction_date, description FROM financial_items "
                "WHERE (cui_source ILIKE :e OR cui_destination ILIKE :e OR description ILIKE :e) "
                "AND document_id IN (SELECT id FROM documents WHERE case_id = :cid) "
                "ORDER BY transaction_date ASC"
            ), {"e": f"%{entity_name}%", "cid": self.case_id}).fetchall()
            
            if not tx_res: return f"No timeline events found for '{entity_name}'."
            
            output = f"--- TIMELINE FOR {entity_name} ---\n"
            for r in tx_res:
                output += f"[{r[0]}] {r[1]}\n"
            return output

    def tool_calculate(self, expr: str):
        """Tool 4: Deterministic Python math."""
        try:
            expr = re.sub(r'[^0-9\+\-\*\/\.\(\), ]', '', expr)
            return f"MATH RESULT: {eval(expr):,.2f}"
        except: return "Math error: invalid expression."

    def run(self):
        yield json.dumps({"type": "status", "data": "Forensic Agent is thinking..."})
        
        system_prompt = """You are a Professional Forensic Data Auditor equipped with PROGRESSIVE WORKING MEMORY.
CORE RULES:
1. AGNOSTICISM: You have no prior knowledge of any persons or events. Answer ONLY using evidence from tools or provided context.
2. ATOMIC TARGET RESOLUTION: The question is decomposed into atomic targets in your WORKING MEMORY.
   - Use SEARCH_TEXT or SEARCH_STRUCTURED_DATA to find evidence.
   - For each target where conclusive evidence is found with citations, treat it as Confidence: HIGH and record the verified fact.
   - If evidence for a target is partial or ambiguous, treat it as Confidence: MEDIUM. You MUST use FETCH_FULL_DOCUMENT(doc_id) to inspect the complete document context or surrounding paragraphs before concluding.
3. FINAL RECOMPOSITION: When all targets have reached Confidence: HIGH (either resolved with facts or verified NOT FOUND in all documents), immediately output the [FINAL RESPONSE] synthesizing all verified findings.
4. LANGUAGE: Think in English, but the FINAL ANSWER must be in ROMANIAN.
5. PRECISION: Extract specific facts (names, dates, amounts). If info is missing, state it clearly.
6. SCOPE: Answer strictly the current question. When a new entity or subject is introduced, answer exclusively using evidence for that query without including past topics or unrelated entities.
7. CITATIONS: Every fact MUST be cited using [x], matching the [REF x] from observations.
8. FINALITY: If you have sufficient evidence to answer all targets, you MUST provide the [FINAL RESPONSE] immediately, even in the first or second step.

FINAL RESPONSE FORMAT (ROMANIAN):
[FACTS]
- List of specific facts and unique entities found with citations [x], addressing each target.
[ANALYSIS]
- Brief reasoning connecting the facts. Highlight [CONTRADICTIONS] here.
[CONCLUSION]
- The direct answer to the user's question addressing all decomposed targets.
[MISSING EVIDENCE]
- Relevant data that was NOT found (or "N/A" if all targets were fully confirmed).
[CONFIDENCE]: LOW/MEDIUM/HIGH"""
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "SEARCH_STRUCTURED_DATA",
                    "description": "Find and aggregate records from tables. Use this for COUNTING entities, finding amounts, or specific records. Set aggregate=True for deduplicated counts. If you need a comprehensive list of unique rows, set a higher limit.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subject": {"type": "string", "description": "Entity or keyword to find in table rows."},
                            "match_pattern": {"type": "string", "description": "Optional pattern to filter rows (case-insensitive)."},
                            "aggregate": {"type": "boolean", "description": "If true, returns a deduplicated count and unique records instead of raw text."},
                            "limit": {"type": "integer", "description": "Maximum number of unique records to return (defaults to 100. Set to 100 to avoid performance bottleneck/GPU thrashing)."}
                        },
                        "required": ["subject"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "SEARCH_TEXT",
                    "description": "Search the full text and tables of all case documents. Use this to find textual records, technical specifications, reports, minutes, contracts, declarations, or unstructured evidence.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "concept": {"type": "string", "description": "Keywords, entity names, identifiers, or dates to search."},
                            "semantic_intent": {"type": "string", "description": "Optional type of document (e.g. RAPORT, CONTRACT, DECLARATIE, PROCES VERBAL)."}
                        },
                        "required": ["concept"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "FETCH_FULL_DOCUMENT",
                    "description": "Retrieve the complete text (up to 4096 characters or expanded context window) of a specific document ID. Use this when confidence for a target is MEDIUM to inspect surrounding paragraphs or verify details.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "doc_id": {"type": "integer", "description": "Document ID to inspect in full."},
                            "focus_terms": {"type": "string", "description": "Optional keywords to center the expanded window around."}
                        },
                        "required": ["doc_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "EXPLORE_GRAPH",
                    "description": "Find relationships and links between entities.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity": {"type": "string", "description": "Entity name to explore"}
                        },
                        "required": ["entity"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "CALCULATE",
                    "description": "Perform math calculations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string", "description": "Math expression (e.g. 1500 + 200)"}
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "TIMELINE",
                    "description": "Get a chronological timeline of events for an entity.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity": {"type": "string", "description": "Entity name to track"}
                        },
                        "required": ["entity"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "DETECT_FINANCIAL_ANOMALIES",
                    "description": "Run forensic statistical anomaly detection: Benford's Law deviation, smurfing/split-invoicing, duplicate payments, and round number clustering across case transactions.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add chat history
        messages.extend(self.history)
        
        # Add current question with injected evidence
        messages.append({
            "role": "user", 
            "content": f"EVIDENCE ALREADY IN CONTEXT:\n{self.injected_evidence}\n\nQUESTION: {self.user_question}\n\nREMINDER: You are an Agnostic Auditor. If the answer is in the context above, give the [FINAL RESPONSE] now. If not, use tools. Deduplicate names and follow exclusion rules (e.g. no absentees)."
        })

        has_used_tools = False
        has_used_search_text = False

        for step in range(1, 16):
            yield json.dumps({"type": "step", "data": f"Phase {step}: Investigating..."})
            
            # Tools are always available
            current_tools = tools
            
            # If the model tries to end without evidence after phase 1
            if step > 1 and not has_used_tools and step < 4:
                messages.append({"role": "user", "content": "You haven't used any tools yet. Use SEARCH_TEXT or SEARCH_STRUCTURED_DATA to find evidence before concluding."})
            
            chat_ctx = int(UnifiedLLMClient.get_engine_config().get("chat_ctx", 16384))
            try:
                chat_res = UnifiedLLMClient.chat_step(
                    messages=messages,
                    tools=current_tools,
                    model=self.active_model,
                    temperature=0.0,
                    num_ctx=chat_ctx
                )
                assistant_msg = {
                    "role": "assistant",
                    "content": chat_res.get("content", ""),
                    "tool_calls": chat_res.get("tool_calls", [])
                }
            except Exception as e:
                yield json.dumps({"type": "final", "data": f"Eroare LLM Engine (Timeout/500): {e}"})
                return

            messages.append(assistant_msg)
            
            # Yield thinking/reasoning if present
            content = assistant_msg.get("content", "").strip()
            
            # FAIL-SAFE: If model writes tool calls in text instead of using tool_calls field
            synthetic_tool_calls = []
            if not assistant_msg.get("tool_calls"):
                if "[SEARCH_STRUCTURED_DATA]" in content:
                    # Basic extraction for Qwen's common text-calling format
                    subject_match = re.search(r"subject:\s*([^\\n]+)", content)
                    if subject_match:
                        synthetic_tool_calls.append({
                            "function": {
                                "name": "SEARCH_STRUCTURED_DATA",
                                "arguments": {"subject": subject_match.group(1).strip()}
                            }
                        })
                elif "[SEARCH_TEXT]" in content:
                    concept_match = re.search(r"concept:\s*([^\\n]+)", content)
                    if concept_match:
                        has_used_search_text = True
                        synthetic_tool_calls.append({
                            "function": {
                                "name": "SEARCH_TEXT",
                                "arguments": {"concept": concept_match.group(1).strip()}
                            }
                        })

            if content:
                yield json.dumps({"type": "observation", "data": f"Thinking: {content}"})

            # Check if tools were called (real or synthetic)
            tool_calls = assistant_msg.get("tool_calls", []) or synthetic_tool_calls
            
            if tool_calls:
                has_used_tools = True
                for tc in tool_calls:
                    t_name = tc["function"]["name"]
                    t_args = tc["function"]["arguments"]
                    if t_name == "SEARCH_TEXT":
                        has_used_search_text = True
                    
                    if isinstance(t_args, str):
                        try:
                            t_args = json.loads(t_args)
                        except:
                            t_args = {"subject": t_args, "concept": t_args, "entity": t_args, "expression": t_args}
                            
                    if isinstance(t_args, dict):
                        subject_val = t_args.get("subject", "")
                        if isinstance(subject_val, str) and "\n" in subject_val:
                            lines = subject_val.split("\n")
                            t_args["subject"] = lines[0].replace("- subject:", "").replace("subject:", "").strip()
                            for line in lines[1:]:
                                if "aggregate" in line.lower():
                                    t_args["aggregate"] = "true" in line.lower()
                                if "match_pattern" in line.lower():
                                    t_args["match_pattern"] = line.split(":")[-1].strip().strip("'\"")
                                if "date_filter" in line.lower():
                                    t_args["date_filter"] = line.split(":")[-1].strip().strip("'\"")
                                    
                    yield json.dumps({"type": "tool_call", "tool": t_name, "params": str(t_args)})
                    
                    observation = ""
                    if t_name == "SEARCH_STRUCTURED_DATA":
                        observation = self.tool_search_transactions(
                            subject=t_args.get("subject", "") if isinstance(t_args, dict) else "", 
                            date_filter=t_args.get("date_filter", "") if isinstance(t_args, dict) else "",
                            match_pattern=t_args.get("match_pattern", "") if isinstance(t_args, dict) else "",
                            aggregate=t_args.get("aggregate", False) if isinstance(t_args, dict) else False,
                            limit=int(t_args.get("limit", 30)) if isinstance(t_args, dict) and t_args.get("limit") is not None else 30
                        )
                    elif t_name == "SEARCH_TEXT":
                        observation = self.tool_search_text(t_args.get("concept", ""), t_args.get("semantic_intent", ""))
                    elif t_name == "FETCH_FULL_DOCUMENT":
                        observation = self.tool_fetch_full_document(
                            doc_id=int(t_args.get("doc_id", 0)) if isinstance(t_args, dict) else 0,
                            focus_terms=t_args.get("focus_terms", "") if isinstance(t_args, dict) else ""
                        )
                    elif t_name == "EXPLORE_GRAPH":
                        observation = self.tool_explore_graph(t_args.get("entity", ""))
                    elif t_name == "TIMELINE":
                        observation = self.tool_timeline(t_args.get("entity", ""))
                    elif t_name == "CALCULATE":
                        observation = self.tool_calculate(t_args.get("expression", ""))
                    elif t_name == "DETECT_FINANCIAL_ANOMALIES":
                        from .anomaly_service import anomaly_service
                        with SessionLocal() as db:
                            res = anomaly_service.analyze_case(self.case_id, db)
                            observation = json.dumps(res, indent=2, ensure_ascii=False)
                    else:
                        observation = "Unknown tool."
                    
                    yield json.dumps({"type": "observation", "data": observation[:2500]})
                    
                    tool_msg = {
                        "role": "tool",
                        "content": observation
                    }
                    if tc.get("id"):
                        tool_msg["tool_call_id"] = tc["id"]
                    messages.append(tool_msg)
                continue # Go to next iteration to let model think about the observation
            
            # If no tools called, we check if we have the final answer
            final_content = assistant_msg.get("content", "").strip()
            
            is_final_candidate = (
                "[FINAL RESPONSE]" in final_content or 
                "[FACTS]" in final_content or 
                "[CONCLUSION]" in final_content or 
                "CONCLUZIE" in final_content.upper() or
                "[CONCLUZIE]" in final_content or
                "CONFIDENCE: HIGH" in final_content.upper()
            )
            
            if is_final_candidate and has_used_tools:
                # Extract clean final response part if it's mixed with planning/thinking
                if "[FINAL RESPONSE]" in final_content:
                    parts = final_content.split("[FINAL RESPONSE]")
                    display_content = parts[-1].strip()
                    if not display_content and len(parts) > 1 and parts[0].strip():
                        display_content = parts[0].strip()
                else:
                    display_content = final_content
                
                if display_content:
                    yield json.dumps({"type": "final", "data": display_content, "citations": self.citations})
                    return

            if not has_used_tools and step < 4:
                messages.append({"role": "user", "content": "Continuă investigația folosind uneltele (SEARCH_TEXT, FETCH_FULL_DOCUMENT, SEARCH_STRUCTURED_DATA) pentru a găsi dovezi clare înainte de a concluziona."})
                continue
                
            if final_content and has_used_tools:
                yield json.dumps({"type": "final", "data": final_content, "citations": self.citations})
                return

        yield json.dumps({"type": "final", "data": "Am atins limita de 15 pași de investigație. Rezumat parțial bazat pe dovezile găsite:", "citations": self.citations})

def query_investigator(case_id: int, user_question: str):
    agent = AgenticInvestigator(case_id, user_question)
    full_text = ""
    for chunk_json in agent.run():
        chunk = json.loads(chunk_json)
        if chunk.get("type") == "final": 
            full_text = chunk["data"]
            break
    return {"answer": full_text, "citations": agent.citations}
