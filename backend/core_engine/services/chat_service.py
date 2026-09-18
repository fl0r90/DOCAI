# TEST_SYNC_12345
import os
import requests
import json
import re
import time
import logging
import redis
from typing import List, Dict, Tuple, Optional, Any

logger = logging.getLogger(__name__)
from sqlalchemy import text, or_, and_
from ..database import engine, SessionLocal
from ..core.config import get_llm_config, get_active_model_name
from ..models import DocumentChunk, Document, ChatMessage, Case
from .. import models
from .graph_service import GraphService
from .llm_client import UnifiedLLMClient, ChatStoppedError
from .debug_logger import debug_logger

_r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

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
        clauses = re.split(r"[\?,;]|\b(?:si|și|precum și)\s+(?=(?:cum|ce|care|cine|de ce|cât|cat|când|cand|unde)\b)", parts[1], flags=re.IGNORECASE)
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
        # Coordinate split: only split when followed by an interrogative/question adverb to avoid fragmenting noun phrases
        clauses = re.split(r"\b(?:si|și|precum și)\s+(?=(?:cum|ce|care|cine|de ce|cât|cat|când|cand|unde)\b)", q, flags=re.IGNORECASE)
        if len(clauses) > 1 and all(len(c.strip()) > 8 for c in clauses):
            targets = [c.strip() for c in clauses if c.strip()]

    if not targets:
        targets = [q.strip()]
        
    return targets

class AgenticInvestigator:
    def __init__(self, case_id: int, user_question: str):
        self.case_id = case_id
        # Curățăm artefacte de copiere din terminal (box drawing │, |, etc.) și whitespace redundant
        cleaned_q = re.sub(r'[│┃┆┇┊┋|┌┐└┘├┤┬┴┼─━]', ' ', user_question)
        cleaned_q = re.sub(r'\s+', ' ', cleaned_q).strip()
        if re.match(r'^e\s+(investiga|raport|clauz|factur|contract|document|litigi|disput)', cleaned_q, re.IGNORECASE):
            cleaned_q = "C" + cleaned_q
        self.user_question = cleaned_q
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
        self.searched_queries = []
        self._load_history()
        self._pre_process_query()

    def _extract_unsearched_key_terms(self) -> list:
        """Identifică agnostic termenii cheie (coduri tehnice, entități, canale) din întrebare care nu au fost căutați."""
        STOP_WORDS = {
            "verifică", "verifica", "există", "exista", "care", "ce", "dacă", "daca", 
            "compara", "analizează", "analizeaza", "unde", "când", "cand", "cum", 
            "please", "verify", "check", "what", "where", "when", "how", "total", "suma", "sumă",
            "despre", "intre", "între", "toate", "toți", "toti", "prin", "pentru"
        }
        compound = [
            t for t in re.findall(r"\b[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)+\b", self.user_question)
            if len(t) >= 4 and (any(c.isdigit() for c in t) or t.isupper())
        ]
        entities = [
            w for w in re.findall(r"\b[A-Z][a-zA-Z0-9_]{2,}\b", self.user_question) 
            if w.lower() not in STOP_WORDS and len(w) >= 3
        ]
        raw_terms = list(dict.fromkeys(compound + entities))
        unique_terms = [t for t in raw_terms if not any(t != other and t in other for other in raw_terms)]
        
        unsearched = [
            t for t in unique_terms 
            if not any(t.lower() in sq.lower() for sq in self.searched_queries)
        ]
        return unsearched

    def _stop_check(self) -> bool:
        """Verifică flag-ul de stop din Redis (setat de POST /cases/{id}/chat/stop)."""
        try:
            return bool(_r.exists(f"chat_stop_{self.case_id}"))
        except Exception:
            return False

    def _render_scratchpad(self) -> str:
        lines = ["=== PROGRESSIVE WORKING MEMORY (TEMPORARY SCRATCHPAD) ==="]
        for i, data in self.scratchpad.items():
            status_str = f"[{data['status']} | Confidence: {data['confidence']}]"
            fact_str = f" -> Evidence: {data['fact']} (Ref: {data['citations']})" if data['fact'] else ""
            lines.append(f"Target {i}: {data['target']} | {status_str}{fact_str}")
        lines.append("=========================================================")
        return "\n".join(lines)

    @staticmethod
    def _extract_citation_snippet(text: str, query: str = "", max_len: int = 550) -> Tuple[str, str]:
        """Extrage un extras relevant (snippet) și termenul cheie pentru highlight direct în document.
        
        Returnează:
            (snippet_text, highlight_term)
        """
        if not text:
            return "", ""
        clean = re.sub(r'<!--\s*image\s*-->|\[Doc:[^\]]*\]', '', text, flags=re.IGNORECASE).strip()

        raw_words = [w for w in re.split(r'[\s,.;:?!()\[\]"\'`]+', query or "") if len(w) >= 2]
        stopwords = {
            "care", "este", "sunt", "pentru", "dintre", "catre", "unde", "cand", "cum",
            "ceea", "acest", "acesta", "aceste", "lui", "ei", "lor", "despre", "toate",
            "mult", "mai", "fost", "avut", "face", "avea", "prin", "careva"
        }
        meaningful = [w for w in raw_words if w.lower() not in stopwords]

        def word_priority(w: str):
            is_num = 2 if any(c.isdigit() for c in w) else 0
            is_cap = 1 if w and w[0].isupper() else 0
            return (is_num, is_cap, len(w))

        meaningful.sort(key=word_priority, reverse=True)

        best_pos = -1
        clean_lower = clean.lower()
        for w in meaningful:
            p = clean_lower.find(w.lower())
            if p != -1:
                best_pos = p
                break

        highlight_term = ""
        if best_pos != -1:
            after_text = clean[best_pos:].strip()
            words_after = after_text.split()
            if len(words_after) >= 2:
                highlight_term = f"{words_after[0]} {words_after[1]}".strip(" ,.;:?!()[]\"'")
            elif words_after:
                highlight_term = words_after[0].strip(" ,.;:?!()[]\"'")
            if len(highlight_term) > 40:
                highlight_term = highlight_term[:40].strip()

            half = max_len // 2
            start = max(0, best_pos - half)
            end = min(len(clean), start + max_len)
            if end - start < max_len and start > 0:
                start = max(0, end - max_len)

            if start > 0:
                sp = clean.find(" ", start)
                if sp != -1 and sp < start + 35:
                    start = sp + 1
            if end < len(clean):
                sp = clean.rfind(" ", start, end)
                if sp != -1 and sp > end - 35:
                    end = sp

            prefix = "..." if start > 0 else ""
            suffix = "..." if end < len(clean) else ""
            return prefix + clean[start:end].strip() + suffix, highlight_term

        default_hl = meaningful[0] if meaningful else ""
        return clean[:max_len].strip() + ("..." if len(clean) > max_len else ""), default_hl

    @staticmethod
    def _get_context_budget() -> dict:
        """
        Calculează dinamic bugetul de caractere disponibil pentru injectarea documentelor
        pe baza ferestrei de context active (chat_ctx din system_settings / LLM engine).
        """
        try:
            from ..core.config import get_llm_config
            cfg = get_llm_config()
            chat_ctx = int(cfg.get("chat_ctx", 16384))
        except Exception:
            chat_ctx = 16384

        # Rezervăm tokeni pentru:
        # - System prompt & unelte: ~1200 tokeni
        # - Istoric conversație & întrebare utilizator: ~800 tokeni
        # - Raționament intern (<think>) & sinteză răspuns final: ~1200 tokeni
        reserved_tokens = 3200
        available_tokens = max(4000, chat_ctx - reserved_tokens)

        # Conversie token -> caractere pentru limba română & markdown (~3.5 chars / token)
        max_total_chars = int(available_tokens * 3.5)

        # Limită per document: până la 85% din bugetul total dacă e document unic sau dominant
        doc_context_limit = int(max_total_chars * 0.85)

        return {
            "chat_ctx": chat_ctx,
            "max_total_chars": max_total_chars,
            "doc_context_limit": doc_context_limit
        }

    def _load_history(self):
        """Loads last completed turns (user + assistant pairs) for context window."""
        with SessionLocal() as db:
            past_msgs = db.query(ChatMessage).filter(ChatMessage.case_id == self.case_id).order_by(ChatMessage.created_at.desc()).limit(12).all()
            if not past_msgs:
                return

            # The most recent message in DB is the current user question saved by cases.py - skip it
            if past_msgs[0].role == "user":
                past_msgs = past_msgs[1:]

            turns = []
            i = 0
            while i < len(past_msgs) and len(turns) < 2:
                m = past_msgs[i]
                if m.role == "assistant":
                    clean_asst = m.content.split("**LOG INVESTIGATIE:**")[0].strip()
                    if "FORENSIC STEP:" in clean_asst or "SEARCH_TEXT" in clean_asst:
                        i += 1
                        continue
                    if "[CONCLUSION]" in clean_asst:
                        conclusion_part = clean_asst.split("[CONCLUSION]")[-1].split("[MISSING EVIDENCE]")[0].strip()
                        clean_asst = f"[CONCLUZIE ANTERIOARĂ]: {conclusion_part[:400]}"
                    elif "[CONCLUZIE]" in clean_asst:
                        conclusion_part = clean_asst.split("[CONCLUZIE]")[-1].split("[MISSING EVIDENCE]")[0].strip()
                        clean_asst = f"[CONCLUZIE ANTERIOARĂ]: {conclusion_part[:400]}"
                    elif "[FACTS]" in clean_asst:
                        facts_part = clean_asst.split("[FACTS]")[-1].split("[ANALYSIS]")[0].strip()
                        clean_asst = f"[DATE ANTERIOARE]: {facts_part[:300]}"
                    elif len(clean_asst) > 200:
                        clean_asst = f"[RĂSPUNS ANTERIOR]: {clean_asst[:200]}..."

                    # Ensure paired with the preceding user message
                    if i + 1 < len(past_msgs) and past_msgs[i+1].role == "user":
                        clean_user = re.sub(r'[│┃┆┇┊┋|┌┐└┘├┤┬┴┼─━]', ' ', past_msgs[i+1].content)
                        clean_user = re.sub(r'\s+', ' ', clean_user).strip()
                        if clean_user and clean_asst:
                            turns.append((clean_user, clean_asst))
                        i += 2
                        continue
                i += 1

            for u_text, a_text in reversed(turns):
                self.history.append({"role": "user", "content": u_text})
                self.history.append({"role": "assistant", "content": a_text})
            
            # Truncate history to prevent unbounded growth
            max_history = int(UnifiedLLMClient.get_engine_config().get("max_messages", 12))
            if len(self.history) > max_history:
                self.history = self.history[-max_history:]

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
            
            # Extract document/invoice codes (e.g. FACT-2023-0245, CTR-104, AGR-2024-0089)
            doc_codes = re.findall(r'\b[A-Z]{2,6}[-_/]\d{2,4}[-_/]\d{2,6}\b', self.user_question, re.IGNORECASE)
            if not doc_codes:
                doc_codes = re.findall(r'\b(?:FACT|CTR|AGR|NOR|AVZ|ACT)[-_/0-9]+\b', self.user_question, re.IGNORECASE)

            if anchors or found_months or found_years or found_dates or doc_codes:
                self.injected_evidence = "--- PRELIMINARY CONTEXT ---\n"
                self.injected_evidence += f"Detected Subject(s): {', '.join(anchors) if anchors else 'None'}\n"
                self.injected_evidence += f"Detected Time Constraints: {' '.join(found_months)} {' '.join(found_years)}\n"
                if found_dates:
                    self.injected_evidence += f"Detected Explicit Date Variations to Search: {', '.join(found_dates[:6])}\n"
                if doc_codes:
                    self.injected_evidence += f"Detected Document/Invoice Code(s): {', '.join(doc_codes)}\n"
                    short_codes = []
                    for dc in doc_codes:
                        nums = re.findall(r'\d{2,}', dc)
                        if nums:
                            short_codes.extend([nums[-1], nums[-1].lstrip('0')])
                    short_codes = list(dict.fromkeys(short_codes))
                    if short_codes:
                        self.injected_evidence += f"ACTION RULE: When searching for these codes, run SEARCH_TEXT with just the code alone (e.g. concept='{doc_codes[0]}') to find the invoice/contract, AND search bank statements/transactions with the short number (e.g. concept='{short_codes[0]}' or concept='virament {short_codes[0]}') to locate the payment.\n"
                
        # Agnostic Multi-Domain Intent Detection
        q_lower = self.user_question.lower()
        if re.search(r'\b(cati|câți|cate|câte|totalul|totala|totală|suma totală|sumă totală|listă completă|lista completa)\b', q_lower) or re.search(r'\btotal\b', q_lower):
            self.injected_evidence += "CRITICAL: The user is asking for a QUANTITATIVE answer or a TOTAL COUNT. You MUST use SEARCH_STRUCTURED_DATA to get accurate counts from the database tables. Do NOT rely on individual text fragments for totals.\n"
        elif re.search(r'\b(plata|plăți|incasare|încasare|sume|ron|eur|usd|achizitie|achiziție|pret|preț|valoare|cost|costuri|factura|factură|virament|iban|cont bancar)\b', q_lower):
            self.injected_evidence += "Suggested Intent: FINANCIAL / TABULAR -> Use SEARCH_STRUCTURED_DATA or targeted SEARCH_TEXT for exact amounts, invoices, and transactions.\n"
        elif re.search(r'\b(whatsapp|chat|conversatie|conversație|mesaj|mesaje|discutie|discuție|audio|cine a zis|ce a raspuns|ce a răspuns)\b', q_lower):
            self.injected_evidence += "Suggested Intent: CHAT / WHATSAPP FORENSICS -> Chronological communication audit. Inspect sender/recipient identities, exact timestamps, reply sequence, and informal agreements or contradictions against formal documents.\n"
        elif re.search(r'\b(contract|contractul|clauza|clauză|clauze|penalitati|penalități|termen|reziliere|obligatii|obligații|semnat|semnatar|anexa|anexă)\b', q_lower):
            self.injected_evidence += "Suggested Intent: CONTRACTUAL / LEGAL AUDIT -> Review contractual terms, defined parties, specific liabilities, penalty clauses, and signature/annex sections.\n"
        elif re.search(r'\b(tot parcursul|toata cartea|toată cartea|evolutia|evoluția|de la debut|complet|exhaustiv|sinteză globală|sinteza globala|toate capitolele|toata conversatia|toată conversația)\b', q_lower):
            self.injected_evidence += "Suggested Intent: EXHAUSTIVE DOCUMENT AUDIT -> Use ROLLING_SCRATCHPAD_AUDIT to traverse all document chapters/pages and accumulate a comprehensive forensic scratchpad without missing any section.\n"
        else:
            self.injected_evidence += "Suggested Intent: CONTEXTUAL / TEXTUAL -> Use SEARCH_TEXT for document details.\n"

        # Positional Clue Detection (End / Epilogue vs Start / Preamble)
        if any(k in q_lower for k in ["la final", "la sfârșit", "la sfarsit", "epilog", "concluzia cărții", "concluzia cartii", "ultimele pagini", "încheiere", "incheiere"]):
            self.injected_evidence += "POSITIONAL ANCHOR: The user inquiry specifically targets the END / EPILOGUE / CONCLUDING sections of the document. Prioritize the final pages and concluding chapters.\n"
        elif any(k in q_lower for k in ["la început", "la inceput", "debut", "preambul", "articolul 1", "introducere", "primele pagini"]):
            self.injected_evidence += "POSITIONAL ANCHOR: The user inquiry specifically targets the START / PREAMBLE / INTRODUCTION of the document. Prioritize the initial pages and opening clauses.\n"
                
        if anchors:
            self.injected_evidence += "Relational Check: Entities detected. EXPLORE_GRAPH may provide links.\n"

        if self.scratchpad:
            self.injected_evidence += "\n" + self._render_scratchpad() + "\n"
        
        self.injected_evidence += "Use the specialized tools below to find exact records.\n"

    def tool_inspect_forensic_ledger(self, query: str = "", doc_id: int = 0):
        """Tool: Search and inspect the pre-extracted granular forensic ledger (structured sections, key legal clauses, entities, financials)."""
        if self._stop_check():
            raise ChatStoppedError("Stop request received before ledger inspection.")
        with SessionLocal() as db:
            docs_query = db.query(Document).filter(Document.case_id == self.case_id)
            if doc_id > 0:
                docs_query = docs_query.filter(Document.id == doc_id)
            docs = docs_query.all()
            if not docs:
                return "No documents found in this case."

            q_terms = [w.lower() for w in re.findall(r'\b\w{2,}\b', query)] if query else []
            matches = []

            for d in docs:
                meta = d.doc_metadata if isinstance(d.doc_metadata, dict) else {}
                ledger = meta.get("forensic_ledger", [])
                if not ledger:
                    summary = d.ai_summary or ""
                    if summary:
                        matches.append((1, f"Document: {d.filename} (ID {d.id})\n[Raport Executiv]:\n{summary[:1500]}"))
                    continue

                for chunk_item in ledger:
                    c_text = chunk_item.get("dossier_text", "")
                    p_start = chunk_item.get("page_start", 1)
                    p_end = chunk_item.get("page_end", 1)
                    idx = chunk_item.get("chunk_idx", 1)
                    tot = chunk_item.get("total_chunks", 1)

                    if not q_terms:
                        matches.append((1, f"Document: {d.filename} (ID {d.id}) | Secțiunea {idx}/{tot} (Pag. {p_start}-{p_end}):\n{c_text}"))
                    else:
                        match_count = sum(1 for term in q_terms if term in c_text.lower())
                        if match_count > 0:
                            matches.append((match_count, f"Document: {d.filename} (ID {d.id}) | Secțiunea {idx}/{tot} (Pag. {p_start}-{p_end}):\n{c_text}"))

            if not matches:
                return f"Nu s-au găsit mențiuni relevante în dosarul de audit pentru '{query}'. Folosește SEARCH_TEXT pentru căutare în textul brut."

            matches.sort(key=lambda x: x[0], reverse=True)
            selected = [m[1] for m in matches[:4]]

            citation_id = len(self.citations) + 1
            self.citations.append({
                "id": citation_id,
                "doc_id": docs[0].id,
                "page": 1,
                "content": selected[0][:400],
                "highlight_term": query[:30] if query else "",
                "filename": docs[0].filename,
                "spatial": "forensic_ledger"
            })

            return f"[REF {citation_id} - FORENSIC AUDIT DOSSIER]:\n\n" + "\n\n---\n\n".join(selected) + "\n\n💡 NOTĂ PENTRU INVESTIGATOR: Dacă ai nevoie de textul cuvânt cu cuvânt al unei clauze sau de cifre brute detaliate din paginile menționate mai sus, apelează SEARCH_TEXT(concept='...', doc_id=X, page_start=Y, page_end=Z) pentru zoom chirurgical cu reranker-ul!"

    def tool_search_text(self, query: str, semantic_intent: str = "", doc_id: int = 0, page_start: int = 0, page_end: int = 0):
        """Tool 1: Hybrid Search (Lexical + Vector + Date-Aware) in document chunks with optional targeted page zoom."""
        if self._stop_check():
            raise ChatStoppedError("Stop request received before hybrid search.")
        with SessionLocal() as db:
            all_docs = db.query(Document).filter(Document.case_id == self.case_id).all()
            if doc_id and doc_id > 0:
                target_doc_ids = [d.id for d in all_docs if d.id == doc_id]
            else:
                target_doc_ids = [d.id for d in all_docs]
            if not target_doc_ids: return "No documents found in this case."
            
            # Apply semantic intent preference (search in doc_type, filename OR dynamic_attributes)
            intent_doc_ids = set()
            if semantic_intent:
                si_lower = semantic_intent.lower()
                for d in all_docs:
                    if d.id not in target_doc_ids: continue
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
                        intent_doc_ids.add(d.id)
            
            # Base filters for chunks (doc_id + optional page range zoom)
            base_filters = [DocumentChunk.document_id.in_(target_doc_ids)]
            if page_start > 0:
                base_filters.append(DocumentChunk.page_number >= page_start)
            if page_end > 0:
                base_filters.append(DocumentChunk.page_number <= page_end)

            # Extract date variants from both the query AND the user question
            t_search_start = time.time()
            date_variants = get_date_variants(query)
            if not date_variants and self.user_question:
                date_variants = get_date_variants(self.user_question)

            words = [w.strip() for w in re.findall(r'\b\w{2,}\b', query) if len(w) >= 2]
            if not words and not date_variants:
                return "No valid keywords or dates for text search."

            # 1. Date Exact Search
            date_res = []
            if date_variants:
                date_conditions = [DocumentChunk.content.ilike(f"%{dv}%") for dv in date_variants]
                date_res = db.query(DocumentChunk)\
                    .filter(and_(*base_filters, or_(*date_conditions)))\
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
                    vector_res = db.query(DocumentChunk)\
                        .filter(and_(*base_filters))\
                        .order_by(DocumentChunk.embedding.l2_distance(query_embedding))\
                        .limit(50).all()
                except Exception as e:
                    db.rollback()
                    print(f"[!] pgvector search error: {e}")

            # 3. Lexical Search (Exact Keyword Match via ILIKE)
            lexical_res = []
            lex_words = [w for w in words if len(w) >= 3]
            if lex_words:
                conditions = [DocumentChunk.content.ilike(f"%{w}%") for w in lex_words]
                lexical_res = db.query(DocumentChunk)\
                    .filter(and_(*base_filters, or_(*conditions)))\
                    .limit(100).all()

            # 3a. Compound Token Exact Search (e.g. FACT-2023-0245, CTR-104, AGRO-CHIM)
            compound_res = []
            compound_tokens = re.findall(r'\b[A-Za-z0-9]+(?:[-_/][A-Za-z0-9]+)+\b', query)
            if compound_tokens:
                compound_conditions = [DocumentChunk.content.ilike(f"%{ct}%") for ct in compound_tokens]
                compound_res = db.query(DocumentChunk)\
                    .filter(and_(*base_filters, or_(*compound_conditions)))\
                    .limit(50).all()

            # 3b. Positional Search (End/Epilogue/Signatures vs Start/Preamble)
            positional_res = []
            q_full_lower = (query + " " + (self.user_question or "")).lower()
            critical_keywords = ["final", "sfarsit", "sfârșit", "epilog", "concluzi", "ultim", "anexe", "semnatur", "sumă totală", "prejudiciu", "2013", "2014", "2015", "2016", "2017", "2018", "anexa nr"]
            if any(k in q_full_lower for k in critical_keywords):
                end_chunks = db.query(DocumentChunk)\
                    .filter(and_(*base_filters))\
                    .order_by(DocumentChunk.page_number.desc(), DocumentChunk.id.desc())\
                    .limit(30).all()
                positional_res.extend(reversed(end_chunks))
            elif any(k in q_full_lower for k in ["debut", "inceput", "început", "preambul", "introducere", "articolul 1", "primele"]):
                start_chunks = db.query(DocumentChunk)\
                    .filter(and_(*base_filters))\
                    .order_by(DocumentChunk.page_number.asc(), DocumentChunk.id.asc())\
                    .limit(30).all()
                positional_res.extend(start_chunks)

            # 4. Merge & Deduplicate (compound, date and positional prioritized)
            seen_ids = set()
            merged_results = []
            for r in compound_res + date_res + positional_res + vector_res + lexical_res:
                if r.id not in seen_ids:
                    seen_ids.add(r.id)
                    merged_results.append(r)

            if not merged_results: return "No text fragments found."

            # 5. Neural Reranking via SentenceTransformers (with Rule-based Fallback)
            if self._stop_check():
                raise ChatStoppedError("Stop request received before reranker.")
            scored_res = []
            try:
                from .rerank_service import RerankService
                reranker = RerankService.get_instance()
                # Rerank query with candidates (increased from 20 to 50)
                scored_res = reranker.rerank(query, merged_results, top_k=50)
                print(f"[+] Successfully reranked {len(merged_results)} candidates using cross-encoder.")
                if intent_doc_ids or date_variants:
                    boosted = []
                    for s, r in scored_res:
                        boost = 0.0
                        if intent_doc_ids and r.document_id in intent_doc_ids:
                            boost += 2.0
                        if date_variants:
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

            t_search_dur = (time.time() - t_search_start) * 1000
            debug_logger.recall_metrics(
                query=query,
                vector_count=len(vector_res),
                lexical_count=len(lexical_res),
                compound_count=len(compound_res),
                positional_count=len(positional_res),
                reranked_count=len(scored_res),
                duration_ms=t_search_dur,
                trace_id=str(self.case_id),
                case_id=self.case_id
            )

            # 5. Dynamic Context-Aware Document Assembly
            # Calculează dinamic volumul de text injectat pe măsura ferestrei active (chat_ctx)
            budget = self._get_context_budget()
            DOC_CONTEXT_LIMIT = budget["doc_context_limit"]
            MAX_TOTAL_CHARS = budget["max_total_chars"]
            MAX_DOCS_RETURNED = 8

            final_res = []
            total_chars_accumulated = 0
            doc_chunk_counts = {}

            # Iterăm direct peste rezultatele sortate de reranker
            for s, chunk in scored_res:
                if total_chars_accumulated >= MAX_TOTAL_CHARS:
                    break
                if len(final_res) >= MAX_DOCS_RETURNED:
                    break

                doc_id = chunk.document_id
                doc_chunk_counts[doc_id] = doc_chunk_counts.get(doc_id, 0)
                if doc_chunk_counts[doc_id] >= 3:
                    continue

                doc_obj = db.query(Document).filter(Document.id == doc_id).first()
                if not doc_obj:
                    continue

                page_num = getattr(chunk, 'page_number', 1) or 1

                # Context de înaltă fidelitate:
                # Dacă documentul brut este foarte scurt (<= 3000 chars - ex. factură/aviz), folosim raw_text
                # Altfel, conținutul chunk-ului extras de Docling este semantic, curat și conține fix secțiunea relevantă
                raw_len = len(doc_obj.raw_text.strip()) if (doc_obj.raw_text and doc_obj.raw_text.strip()) else 0
                if doc_obj.raw_text and raw_len <= 3000:
                    doc_context = doc_obj.raw_text.strip()
                else:
                    doc_context = (chunk.content or "").strip()

                if not doc_context:
                    continue

                doc_chunk_counts[doc_id] += 1
                total_chars_accumulated += len(doc_context)
                citation_id = len(self.citations) + 1

                # Extragem un extras relevant (snippet) centrat pe termenii căutați
                best_clean = re.sub(r'<!--\s*image\s*-->|\[Doc:[^\]]*\]', '', chunk.content or "", flags=re.IGNORECASE).strip()
                cite_source = chunk.content if len(best_clean) >= 30 else doc_context
                snippet_text, highlight_term = self._extract_citation_snippet(
                    text=cite_source,
                    query=f"{query} {self.user_question}",
                    max_len=550
                )

                self.citations.append({
                    "id": citation_id,
                    "doc_id": doc_obj.id,
                    "page": page_num,
                    "content": snippet_text,
                    "highlight_term": highlight_term,
                    "filename": doc_obj.filename if doc_obj else "unknown",
                    "spatial": getattr(chunk, "spatial", "") or ""
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

    def _compress_scratchpad(self, scratchpad: str, chat_ctx: int) -> str:
        """Comprimă scratchpad-ul dacă depășește 50% din bugetul de context."""
        max_scratch_chars = int(chat_ctx * 3.5 * 0.5)  # 50% din context
        if len(scratchpad) <= max_scratch_chars:
            return scratchpad
        
        print(f"[SCRATCHPAD] Comprimare necesară: {len(scratchpad):,} > {max_scratch_chars:,} caractere")
        prompt_compress = f"""Comprimă următorul scratchpad forensic în maximum {max_scratch_chars // 2} caractere, păstrând TOATE faptele esențiale, citatele, și concluziile. Elimină redundanțele și detaliile minore.

SCRATCHPAD CURENT:
{scratchpad}

Răspunde EXCLUSIV cu scratchpad-ul comprimat (format bullet-points)."""
        
        try:
            res = UnifiedLLMClient.chat_step(
                messages=[{"role": "user", "content": prompt_compress}],
                tools=None,
                model=self.active_model,
                temperature=0.0,
                num_ctx=chat_ctx,
                stop_check=self._stop_check
            )
            compressed = res.get("content", "").strip()
            if compressed and len(compressed) < len(scratchpad):
                print(f"[SCRATCHPAD] Comprimat de la {len(scratchpad):,} la {len(compressed):,} caractere")
                return compressed
        except Exception as e:
            print(f"[SCRATCHPAD] Eroare la comprimare: {e}")
        
        # Fallback: trunchiază simplu
        return scratchpad[:max_scratch_chars] + "\n[... comprimat automat ...]"

    def _load_scratchpad_state(self, doc_id: int) -> tuple:
        """Încarcă starea salvată a scratchpad-ului din Redis (pentru resume)."""
        key = f"scratchpad_{self.case_id}_{doc_id}"
        try:
            state = _r.get(key)
            if state:
                data = json.loads(state)
                print(f"[SCRATCHPAD] Resume de la calupul {data.get('chunk_idx', 0)}")
                return (
                    data.get("findings", []),
                    data.get("am_gasit", ""),
                    data.get("mai_caut", ""),
                    data.get("chunk_idx", 0)
                )
        except Exception as e:
            print(f"[SCRATCHPAD] Eroare la încărcare stare: {e}")
        return [], "", "", 0

    def _save_scratchpad_state(self, doc_id: int, findings: list, am_gasit: str, mai_caut: str, chunk_idx: int):
        """Salvează starea scratchpad-ului în Redis (pentru resume)."""
        key = f"scratchpad_{self.case_id}_{doc_id}"
        try:
            _r.set(key, json.dumps({
                "findings": findings,
                "am_gasit": am_gasit,
                "mai_caut": mai_caut,
                "chunk_idx": chunk_idx,
                "timestamp": time.time()
            }), ex=3600)  # Expiră în 1 oră
        except Exception as e:
            print(f"[SCRATCHPAD] Eroare la salvare stare: {e}")

    def _clear_scratchpad_state(self, doc_id: int):
        """Șterge starea scratchpad-ului din Redis (după finalizare)."""
        key = f"scratchpad_{self.case_id}_{doc_id}"
        try:
            _r.delete(key)
        except Exception:
            pass

    def run_rolling_scratchpad_digest(self, doc_id: int, focus_query: str):
        """
        Generator de investigație iterativă (Rolling Scratchpad) pentru documente voluminoase/cărți.
        Implementează arhitectura Goal-Conditioned Working State & Append-Only Ledger:
        - Context curat la fiecare calup (nu se acumulează zgomot textual).
        - Stare de lucru de înaltă precizie (CE AM GĂSIT PÂNĂ ACUM vs CE MAI CĂUTĂM).
        - Append-Only Ledger: dovezile concrete sunt păstrate integral în memorie.
        - Early Stop automat când toate obiectivele au fost atinse.
        Produce tupluri: (status_message, is_final, final_observation)
        """
        start_time = time.time()
        
        with SessionLocal() as db:
            doc_obj = None
            if doc_id and doc_id > 0:
                doc_obj = db.query(Document).filter(Document.id == doc_id).first()
            if not doc_obj:
                all_docs = db.query(Document).filter(Document.case_id == self.case_id).all()
                if not all_docs:
                    yield ("Nu există documente în dosar.", True, "No documents found.")
                    return
                doc_obj = max(all_docs, key=lambda d: len(d.raw_text or "") if d.raw_text else 0)

            raw = doc_obj.raw_text.strip() if doc_obj.raw_text else ""
            if not raw:
                chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_obj.id).order_by(DocumentChunk.page_number, DocumentChunk.id).all()
                raw = "\n\n".join([c.content for c in chunks])

            if not raw:
                yield (f"Documentul {doc_obj.filename} nu conține text.", True, "Document contains no extractable text.")
                return

            budget = self._get_context_budget()
            chat_ctx = budget["chat_ctx"]
            doc_limit = budget["doc_context_limit"]

            effective_query = (focus_query or self.user_question or "").strip()

            # Dacă documentul încape lejer într-un singur context, îl returnăm direct
            if len(raw) <= doc_limit:
                citation_id = len(self.citations) + 1
                snippet_text, highlight_term = self._extract_citation_snippet(
                    text=raw,
                    query=effective_query,
                    max_len=550
                )
                self.citations.append({
                    "id": citation_id,
                    "doc_id": doc_obj.id,
                    "page": 1,
                    "content": snippet_text,
                    "highlight_term": highlight_term,
                    "filename": doc_obj.filename,
                    "spatial": "full_text"
                })
                header = f"[REF {citation_id} - FULL DOC: {doc_obj.filename}, Pagina 1]"
                yield ("Documentul încape integral în context.", True, f"{header}:\n{raw}")
                return

            # Calibrare dinamică a calupului (Dynamic Batch Sizing):
            # Lăsăm ~3.000 tokeni pentru prompt de sistem + obiectiv + starea curentă + output scurt
            available_tokens = max(4000, chat_ctx - 3000)
            batch_size = max(18000, int(available_tokens * 3.5))
            overlap = min(2000, max(1000, int(batch_size * 0.05)))

            slices = []
            curr_pos = 0
            while curr_pos < len(raw):
                end_pos = min(len(raw), curr_pos + batch_size)
                slices.append((curr_pos, end_pos, raw[curr_pos:end_pos]))
                if end_pos >= len(raw):
                    break
                curr_pos = end_pos - overlap

            total_batches = len(slices)

            # Încărcăm starea anterioară (resume capability)
            accumulated_findings, am_gasit_deja, mai_caut, resume_idx = self._load_scratchpad_state(doc_obj.id)
            if not mai_caut:
                mai_caut = effective_query
            if not am_gasit_deja:
                am_gasit_deja = "Nicio probă certă identificată încă. Începem investigația de la debutul documentului."

            if resume_idx > 0:
                yield (f"🔄 Reluare Rolling Scratchpad de la calupul {resume_idx + 1}/{total_batches}...", False, "")
            else:
                yield (f"📖 Pornire Rolling Scratchpad pentru '{doc_obj.filename}' ({len(raw):,} car., {total_batches} calupuri de ~{batch_size:,} car.)...", False, "")

            max_retries = 2
            early_stopped = False

            for idx, (s_start, s_end, batch_text) in enumerate(slices, 1):
                if idx <= resume_idx:
                    continue

                if self._stop_check():
                    raise ChatStoppedError("Stop request received during Rolling Scratchpad.")

                elapsed = time.time() - start_time
                pct = int((idx - 1) / total_batches * 100)
                yield (f"📖 [Rolling Scratchpad {idx}/{total_batches}] {pct}% | {elapsed:.0f}s | Analiză fragment ({s_start:,} - {s_end:,} car.)...", False, "")

                success = False
                for attempt in range(max_retries + 1):
                    try:
                        prompt_scratch = f"""Ești un Auditor Investigativ și Criminalist Textual de Elită.
Obiectivul investigației / Întrebarea:
{effective_query}

=== STAREA CURENTĂ A ANCHETEI (Ce știm până acum) ===
CE AM GĂSIT PÂNĂ ACUM:
{am_gasit_deja}

CE MAI CĂUTĂM ÎN ACEST FRAGMENT:
{mai_caut}

=== FRAGMENTUL DE TEXT CURENT (Calupul {idx}/{total_batches} din '{doc_obj.filename}', offset {s_start:,} - {s_end:,} car.) ===
{batch_text}

=== INSTRUCȚIUNI FORENSICE STRICTE ===
1. Analizează textul fragmentului curent exclusiv în raport cu CE MAI CĂUTĂM.
2. Extrage DOAR faptele/clauzele/cifrele/datele NOI apărute în acest fragment care răspund la căutare. Nu repeta ce știm deja.
3. Răspunde STRICT în următorul format (fără alte introduceri sau politețuri):

[NOI_PROBE_IDENTIFICATE]
- (enumeră cu bullet points dovezile noi concrete, cu cifre, nume, clauze, date sau scrie "NICIUNA" dacă fragmentul nu conține elemente relevante)

[ACTUALIZARE_STARE]
AM GĂSIT PÂNĂ ACUM: (sinteză telegrafică de max 2-3 fraze cu tot ce avem confirmat cert până în prezent)
MAI CAUT ÎN CONTINUARE: (ce a rămas de lămurit din obiectiv, sau scrie exact "COMPLET" dacă toate datele necesare au fost găsite în totalitate)"""

                        # Calculate payload size
                        prompt_size = len(prompt_scratch)
                        payload_tokens = prompt_size / 3.5
                        utilization_pct = (payload_tokens / chat_ctx) * 100
                        if utilization_pct > 85:
                            print(f"[SCRATCHPAD] Payload la {utilization_pct:.1f}% din context ({prompt_size:,} caractere)")

                        res = UnifiedLLMClient.chat_step(
                            messages=[{"role": "user", "content": prompt_scratch}],
                            tools=None,
                            model=self.active_model,
                            temperature=0.0,
                            num_ctx=chat_ctx,
                            stop_check=self._stop_check
                        )
                        output_text = res.get("content", "").strip()
                        if output_text:
                            # Parsăm secțiunile
                            probe_noi = ""
                            if "[NOI_PROBE_IDENTIFICATE]" in output_text:
                                parts = output_text.split("[ACTUALIZARE_STARE]")
                                probe_noi = parts[0].replace("[NOI_PROBE_IDENTIFICATE]", "").strip()
                                if len(parts) > 1:
                                    stare_text = parts[1].strip()
                                    m_gasit = re.search(r'AM GĂSIT PÂNĂ ACUM:\s*(.*?)(?=MAI CAUT ÎN CONTINUARE:|$)', stare_text, re.DOTALL | re.IGNORECASE)
                                    m_caut = re.search(r'MAI CAUT ÎN CONTINUARE:\s*(.*?)$', stare_text, re.DOTALL | re.IGNORECASE)
                                    if m_gasit and m_gasit.group(1).strip():
                                        am_gasit_deja = m_gasit.group(1).strip()
                                    if m_caut and m_caut.group(1).strip():
                                        mai_caut = m_caut.group(1).strip()
                            else:
                                probe_noi = output_text

                            if probe_noi and "NICIUNA" not in probe_noi.upper()[:20] and len(probe_noi) > 10:
                                accumulated_findings.append({
                                    "batch_idx": idx,
                                    "total_batches": total_batches,
                                    "offset_range": f"{s_start}-{s_end}",
                                    "findings": probe_noi
                                })

                            success = True
                            self._save_scratchpad_state(doc_obj.id, accumulated_findings, am_gasit_deja, mai_caut, idx)

                            # Verificare Early Stop dacă obiectivul este COMPLET și nu este o cerere transversală
                            is_exhaustive = any(k in effective_query.lower() for k in [
                                "toate capitolele", "toata cartea", "toată cartea", "pe tot parcursul",
                                "evolutia", "evoluția", "exhaustiv", "toate aparitiile", "toate mențiunile"
                            ])
                            if "COMPLET" in mai_caut.upper() and not is_exhaustive and len(accumulated_findings) > 0 and idx >= 2:
                                yield (f"🎯 Toate elementele căutate au fost identificate la calupul {idx}/{total_batches}! Finalizare rapidă...", False, "")
                                early_stopped = True
                                break

                            break
                    except ChatStoppedError:
                        raise
                    except Exception as ex:
                        if attempt < max_retries:
                            wait_time = (attempt + 1) * 2
                            print(f"[SCRATCHPAD] Calup {idx} eșuat (attempt {attempt + 1}): {ex}. Reîncercare în {wait_time}s...")
                            yield (f"⚠️ Calup {idx} eșuat, reîncercare în {wait_time}s...", False, "")
                            time.sleep(wait_time)
                        else:
                            print(f"[SCRATCHPAD] Calup {idx} eșuat definitiv: {ex}")
                            yield (f"❌ Calup {idx} eșuat după reîncercări. Continuăm cu următorul.", False, "")

                if early_stopped:
                    break

            # Curăță starea salvată din Redis
            self._clear_scratchpad_state(doc_obj.id)
            elapsed = time.time() - start_time

            # Asamblarea dosarului final de dovezi
            compiled_findings_blocks = []
            for item in accumulated_findings:
                compiled_findings_blocks.append(
                    f"### Secțiunea {item['batch_idx']}/{total_batches} (Caractere {item['offset_range']}):\n{item['findings']}"
                )
            
            compiled_text = "\n\n".join(compiled_findings_blocks) if compiled_findings_blocks else "Nu au fost identificate probe specifice în fragmentele analizate."

            citation_id = len(self.citations) + 1
            self.citations.append({
                "id": citation_id,
                "doc_id": doc_obj.id,
                "page": 1,
                "content": compiled_text[:500],
                "highlight_term": "",
                "filename": doc_obj.filename,
                "spatial": "rolling_scratchpad_digest"
            })

            final_header = f"[REF {citation_id} - DOSAR PROBE AUDIT ROLLING ({doc_obj.filename} - {'Oprire timpurie la calupul ' + str(idx) if early_stopped else 'Acoperire 100% în ' + str(total_batches) + ' calupuri'})]"
            final_observation = f"{final_header}:\n\nSINTEZĂ PROBE CONFIRMATE:\n{am_gasit_deja}\n\nDETALIU PROBE PE CALUPURI:\n{compiled_text}"

            yield (f"✅ Finalizat Rolling Scratchpad ({len(accumulated_findings)} calupuri cu probe identificate, {elapsed:.0f}s)!", True, final_observation)

    def tool_fetch_full_document(self, doc_id: int, focus_terms: str = ""):
        """Tool: Retrieve complete full-text or progressive scratchpad digest when document exceeds context window."""
        with SessionLocal() as db:
            doc_obj = db.query(Document).filter(Document.id == doc_id).first()
            if not doc_obj:
                return f"Document ID {doc_id} not found."
            
            raw = doc_obj.raw_text.strip() if doc_obj.raw_text else ""
            if not raw:
                chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).order_by(DocumentChunk.page_number, DocumentChunk.id).all()
                raw = "\n\n".join([c.content for c in chunks])
            
            budget = self._get_context_budget()
            DOC_CONTEXT_LIMIT = budget["doc_context_limit"]

            # Dacă documentul depășește bugetul de context, executăm digestia iterativă Rolling Scratchpad
            if len(raw) > DOC_CONTEXT_LIMIT:
                final_obs = ""
                for _, is_final, res in self.run_rolling_scratchpad_digest(doc_id, focus_terms or self.user_question):
                    if is_final:
                        final_obs = res
                return final_obs

            # Altfel, returnăm documentul integral
            citation_id = len(self.citations) + 1
            snippet_text, highlight_term = self._extract_citation_snippet(
                text=raw,
                query=f"{focus_terms} {self.user_question}",
                max_len=550
            )
            self.citations.append({
                "id": citation_id,
                "doc_id": doc_obj.id,
                "page": 1,
                "content": snippet_text,
                "highlight_term": highlight_term,
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
            return f"{header}\n{dyn_meta}\n{raw}"

    def tool_get_document_outline(self, doc_id: int) -> str:
        """Tool: Inspect the structural table of contents (TOC / Outline) of a document with exact page boundaries."""
        with SessionLocal() as db:
            doc = db.query(Document).filter(Document.id == doc_id, Document.case_id == self.case_id).first()
            if not doc:
                return f"Documentul ID {doc_id} nu a fost găsit în acest dosar."
            meta = doc.doc_metadata or {}
            toc_data = meta.get("toc")
            if toc_data:
                from .toc import DocumentTOC
                toc = DocumentTOC(**toc_data)
                return toc.to_readable_text()
            elif meta.get("outline"):
                lines = [f"=== CUPRINS STRUCTURAL '{doc.filename}' ==="]
                for it in meta.get("outline", []):
                    lines.append(f"• [Pag. {it.get('page_start', it.get('page', 1))}] {it.get('title', '')}")
                return "\n".join(lines)
            elif doc.raw_text:
                from .toc import toc_service
                toc = toc_service.generate_toc(doc.raw_text, document_id=doc_id, document_title=doc.filename, use_llm=False)
                return toc.to_readable_text()
            return f"Documentul ID {doc_id} ('{doc.filename}') nu are încă un cuprins disponibil."

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
                    
                    # Extract numeric suffixes from pattern (e.g. FACT-2023-0245 -> '0245', '245')
                    if match_pattern:
                        num_parts = re.findall(r'\d{2,}', match_pattern)
                        for np in num_parts:
                            pattern_variants.append(np.lower())
                            if np.startswith('0') and len(np) > 1:
                                pattern_variants.append(np.lstrip('0').lower())
                    pattern_variants = list(dict.fromkeys(pattern_variants))

                    clean_subject_terms = [t.lower() for t in search_terms if t.lower() not in ["sc", "s.c.", "srl", "s.r.l.", "sa", "s.a.", "pfa", "srl."]]
                    
                    chunk_filter = []
                    if clean_subject_terms:
                        chunk_filter.extend([DocumentChunk.content.ilike(f"%{t}%") for t in clean_subject_terms])
                    else:
                        chunk_filter.append(DocumentChunk.content.ilike(f"%{subject}%"))
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
                                    if any(t in line.lower() for t in clean_subject_terms) or subject.lower() in line.lower():
                                        is_subject_match = True
                                    elif any(t in c_lower for t in clean_subject_terms) and subject.lower() not in ["prezent", "absent"]:
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
                        "highlight_term": "",
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
        
        system_prompt = """You are a Master Forensic Data Auditor equipped with PROGRESSIVE WORKING MEMORY, specialized in multi-domain evidence analysis:
- CONTRACTS & LEGAL AGREEMENTS: Inspect parties, clauses, obligations, liabilities, penalty terms, termination conditions, dates, and signature/annex sections.
- WHATSAPP & DIGITAL CHATS: Reconstruct chronological message streams, sender/recipient identities, exact timestamps, sequence of replies, and informal agreements or contradictions against formal documents.
- FINANCIAL & TABULAR RECORDS: Extract exact amounts, invoices, currency, IBANs, and ledger balances.
- EXTENSIVE DOSSIERS & BOOKS: Track thesis evolution, chapter progression, ideological stances, and concluding philosophies.

CORE RULES:
1. AGNOSTICISM: You have no prior knowledge of any persons, companies, or events. Answer ONLY using evidence from tools or provided context.

2. TOOL SELECTION & HIERARCHICAL RETRIEVAL GUIDE (CHOOSE APPROPRIATELY):
    - INSPECT_FORENSIC_LEDGER: **CALL THIS FIRST** to search the pre-extracted forensic audit dossier (sections, key legal clauses, entities, financials, red flags). If it contains sufficient facts, answer immediately. If it indicates relevant page numbers, use SEARCH_TEXT to zoom in!
    - SEARCH_TEXT: For targeted queries or for SURGICAL ZOOM-IN with the neural reranker on specific pages (page_start, page_end) or documents (doc_id).
    - SEARCH_STRUCTURED_DATA: For counting entities, finding amounts, or specific transaction records from PostgreSQL tables.
    - FETCH_FULL_DOCUMENT(doc_id): For reviewing a full document.
    - ROLLING_SCRATCHPAD_AUDIT(doc_id): Use as the final comprehensive safety net for multi-chapter evolution when simpler searches are insufficient.

3. ATOMIC TARGET RESOLUTION: The question is decomposed into atomic targets in your WORKING MEMORY.
    - Use INSPECT_FORENSIC_LEDGER or SEARCH_TEXT for targeted queries first.
    - If results are incomplete, ambiguous, or you need full document context, use FETCH_FULL_DOCUMENT(doc_id) OR ROLLING_SCRATCHPAD_AUDIT(doc_id).
    - Positional queries: If the inquiry asks about boundary sections (e.g., 'at the end of the book', 'in the preamble', 'signatures', 'annexes'), prioritize the corresponding initial or final sections of the document.
3. STRICT EVIDENCE-ONLY (NO SPECULATION):
   - Never invent or assume facts, names, or locations not present in the citations.
   - If the user asks about specific entities (e.g., a person, a city, an amount, a clause) and your initial search does not mention them, do NOT speculate or substitute with general knowledge. Perform a dedicated SEARCH_TEXT for those exact terms, or explicitly list them under [MISSING EVIDENCE].
4. FINAL RECOMPOSITION: When all targets have reached Confidence: HIGH (either resolved with facts or verified NOT FOUND in all documents), immediately output the [FINAL RESPONSE] synthesizing all verified findings.
5. LANGUAGE: Think in English, but the FINAL ANSWER must be in ROMANIAN.
6. PRECISION: Extract specific facts (names, dates, timestamps, amounts, exact clause numbers).
7. SCOPE: Answer strictly the current question. When a new entity or subject is introduced, answer exclusively using evidence for that query without including past topics or unrelated entities.
8. CITATIONS: Every fact MUST be cited using [x], matching the [REF x] from observations.
9. FINALITY: If you have sufficient evidence to answer all targets, you MUST provide the [FINAL RESPONSE] immediately, even in the first or second step.
10. INVESTIGATION PLAN PROTOCOL (MANDATORY IN STEP 1):
Before issuing search queries, you MUST understand the full inquiry and decompose it into a structured plan:
- Identify all document identifiers, codes, parties, entities, and channels mentioned.
- Specify the exact evidence needed from each source (e.g., dispatched quantity from delivery notice, received quantity from scale slips, prices/amounts from invoice, informal statements from chat).
- MULTI-SOURCE INQUIRIES: If the question asks about multiple sources (e.g. formal documents AND informal chat/messages/person), you MUST search for evidence for EVERY individual source before concluding. Never skip a channel or person mentioned in the inquiry.
- Execute targeted tool calls strictly for those identifiers or entities. NEVER search for random generic words (e.g. "financiar", "rezultat", "note"). Search exclusively for exact codes, names, or technical terms.

FINAL RESPONSE FORMAT (ROMANIAN):
[FACTS]
- List of specific facts and unique entities found with citations [x], addressing each target.
[ANALYSIS]
- Brief reasoning connecting the facts. Highlight [CONTRADICTIONS] (e.g. between chat messages and contracts, or between different testimonies).
[CONCLUSION]
- The direct answer to the user's question addressing all decomposed targets.
[MISSING EVIDENCE]
- Relevant data that was NOT found (or "N/A" if all targets were fully confirmed).
[CONFIDENCE]: LOW/MEDIUM/HIGH"""
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "ROLLING_SCRATCHPAD_AUDIT",
                    "description": "Read and audit an entire large document (or book/dossier) across ALL pages using progressive rolling context windows and an accumulating scratchpad. Guarantees 100% full-text coverage without missing early, middle, or ending chapters. Ideal for complex multi-chapter synthesis, comparative analysis, or exhaustive evidence gathering.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "doc_id": {"type": "integer", "description": "Document ID to audit in full. If omitted or 0, audits the primary/largest document in the case."},
                            "focus_query": {"type": "string", "description": "The specific question, topics, or themes to track and extract across all pages."}
                        },
                        "required": ["focus_query"]
                    }
                }
            },
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
                    "name": "INSPECT_FORENSIC_LEDGER",
                    "description": "Search and inspect the high-density forensic audit ledger of the documents in the case. Use this FIRST to see which sections/pages contain the answers before running expensive scans. If this tool provides sufficient evidence, answer immediately. If you need verbatim clauses or exact numbers, call SEARCH_TEXT with page_start and page_end to zoom in.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Keywords, topics, legal clauses, entities, or questions to look up in the forensic ledger."},
                            "doc_id": {"type": "integer", "description": "Optional document ID to inspect specifically."}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "SEARCH_TEXT",
                    "description": "Search the full text and tables of all case documents using Hybrid Search (pgvector + lexical + neural reranker). Supports surgical zoom-in on specific page ranges or document IDs.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "concept": {"type": "string", "description": "Keywords, entity names, identifiers, or dates to search."},
                            "semantic_intent": {"type": "string", "description": "Optional type of document (e.g. RAPORT, CONTRACT, DECLARATIE, PROCES VERBAL)."},
                            "doc_id": {"type": "integer", "description": "Optional specific document ID to target."},
                            "page_start": {"type": "integer", "description": "Optional starting page number for surgical reranker zoom-in."},
                            "page_end": {"type": "integer", "description": "Optional ending page number for surgical reranker zoom-in."}
                        },
                        "required": ["concept"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "FETCH_FULL_DOCUMENT",
                    "description": "Retrieve the complete text (dynamically sized to match the active context window) of a specific document ID. Use this when confidence for a target is MEDIUM to inspect surrounding paragraphs or verify details.",
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
                    "name": "GET_DOCUMENT_OUTLINE",
                    "description": "Inspect the structural table of contents (TOC / Outline) of a document: chapters, articles, clauses, annexes, and scale tickets with exact page numbers. Call this to locate relevant sections before fetching chunks.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "doc_id": {"type": "integer", "description": "Document ID to inspect table of contents."}
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
            "content": f"EVIDENCE ALREADY IN CONTEXT:\n{self.injected_evidence}\n\nQUESTION: {self.user_question}\n\nREMINDER: You are an Agnostic Forensic Auditor. Follow these rules STRICTLY:\n1. If the question asks about FINAL amounts, conclusions, annexes (e.g., 'sumă totală', 'prejudiciu final', 'anexa nr', 'concluzii'), you MUST use ROLLING_SCRATCHPAD_AUDIT immediately - DO NOT rely on partial SEARCH_TEXT results.\n2. If the question spans multiple years (e.g., 2013-2018), you MUST use ROLLING_SCRATCHPAD_AUDIT to ensure complete temporal coverage.\n3. If your initial searches return incomplete evidence or low confidence, AMPLIFY by using ROLLING_SCRATCHPAD_AUDIT before concluding.\n4. NEVER conclude that a document section is missing without first trying ROLLING_SCRATCHPAD_AUDIT for comprehensive analysis.\n5. When searching for payments, invoices, or deliveries, search both the full alphanumeric reference and the numeric identifier across bank statements, ledgers, and delivery documents.\n6. Compute exact math on any figures, dates, delays, quantities, or financial differences asked in the question.\n7. CURRENT QUERY FOCUS: Answer ONLY the current question. Ignore past topics, codes, or entities from previous conversation turns unless explicitly asked again.\n8. STRUCTURED INVESTIGATION PLAN: In Phase 1, decompose the question into a structured plan identifying each document code, entity, and quantity/clause needed. DO NOT query random generic words; query the specific codes, entities, and technical terms identified in your plan."
        })

        has_used_tools = False
        has_used_search_text = False

        for step in range(1, 16):
            if self._stop_check():
                yield json.dumps({"type": "final", "data": "Investigație oprită de utilizator.", "citations": self.citations})
                return
            yield json.dumps({"type": "step", "data": f"Phase {step}: Investigating..."})
            debug_logger.step_start(session_id=str(self.case_id), step=step, action="INVESTIGATION_STEP", case_id=self.case_id)
            
            # Tools are always available
            current_tools = tools
            
            # If the model tries to end without evidence after phase 1
            if step > 1 and not has_used_tools and step < 4:
                messages.append({"role": "user", "content": "You haven't used any tools yet. Use SEARCH_TEXT or SEARCH_STRUCTURED_DATA to find evidence before concluding."})
            
            # Truncate messages to prevent context overflow and timeouts
            max_messages = int(UnifiedLLMClient.get_engine_config().get("max_messages", 12))
            messages = truncate_messages(messages, max_messages)
            
            chat_ctx = int(UnifiedLLMClient.get_engine_config().get("chat_ctx", 16384))
            try:
                chat_res = UnifiedLLMClient.chat_step(
                    messages=messages,
                    tools=current_tools,
                    model=self.active_model,
                    temperature=0.0,
                    num_ctx=chat_ctx,
                    stop_check=self._stop_check
                )
                assistant_msg = {
                    "role": "assistant",
                    "content": chat_res.get("content", ""),
                    "tool_calls": chat_res.get("tool_calls", [])
                }
            except ChatStoppedError:
                yield json.dumps({"type": "final", "data": "Investigație oprită de utilizator.", "citations": self.citations})
                return
            except Exception as e:
                err_msg = str(e)
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        resp_text = e.response.text[:2000]
                        if resp_text != err_msg:
                            err_msg = f"{err_msg} | Response: {resp_text}"
                    except Exception:
                        pass
                yield json.dumps({"type": "final", "data": f"Eroare LLM Engine (Timeout/500): {err_msg}"})
                return

            messages.append(assistant_msg)
            
            # Yield thinking/reasoning if present
            reasoning_text = chat_res.get("reasoning")
            if reasoning_text:
                yield json.dumps({"type": "thought", "data": str(reasoning_text).strip()})

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
                elif "[ROLLING_SCRATCHPAD_AUDIT]" in content:
                    query_match = re.search(r"focus_query:\s*([^\\n]+)", content)
                    doc_match = re.search(r"doc_id:\s*(\d+)", content)
                    synthetic_tool_calls.append({
                        "function": {
                            "name": "ROLLING_SCRATCHPAD_AUDIT",
                            "arguments": {
                                "doc_id": int(doc_match.group(1)) if doc_match else 0,
                                "focus_query": query_match.group(1).strip() if query_match else self.user_question
                            }
                        }
                    })
                elif "[FETCH_FULL_DOCUMENT]" in content:
                    doc_match = re.search(r"doc_id:\s*(\d+)", content)
                    focus_match = re.search(r"focus_terms:\s*([^\\n]+)", content)
                    synthetic_tool_calls.append({
                        "function": {
                            "name": "FETCH_FULL_DOCUMENT",
                            "arguments": {
                                "doc_id": int(doc_match.group(1)) if doc_match else 0,
                                "focus_terms": focus_match.group(1).strip() if focus_match else ""
                            }
                        }
                    })
                elif "[INSPECT_FORENSIC_LEDGER]" in content:
                    query_match = re.search(r"query:\s*([^\\n]+)", content)
                    doc_match = re.search(r"doc_id:\s*(\d+)", content)
                    synthetic_tool_calls.append({
                        "function": {
                            "name": "INSPECT_FORENSIC_LEDGER",
                            "arguments": {
                                "query": query_match.group(1).strip() if query_match else self.user_question,
                                "doc_id": int(doc_match.group(1)) if doc_match else 0
                            }
                        }
                    })
                elif "[GET_DOCUMENT_OUTLINE]" in content:
                    doc_match = re.search(r"doc_id:\s*(\d+)", content)
                    synthetic_tool_calls.append({
                        "function": {
                            "name": "GET_DOCUMENT_OUTLINE",
                            "arguments": {
                                "doc_id": int(doc_match.group(1)) if doc_match else 0
                            }
                        }
                    })

            if content:
                yield json.dumps({"type": "observation", "data": f"Thinking: {content}"})

            # Check if tools were called (real or synthetic)
            tool_calls = assistant_msg.get("tool_calls", []) or synthetic_tool_calls
            
            # Debug: log raw tool calls for troubleshooting
            debug_logger.tool_raw(raw_calls=tool_calls, trace_id=str(self.case_id))
            print(f"[TOOL_DEBUG] Raw tool_calls from LLM: {assistant_msg.get('tool_calls', [])}")
            print(f"[TOOL_DEBUG] Synthetic tool_calls: {synthetic_tool_calls}")
            
            if tool_calls:
                has_used_tools = True
                for tc in tool_calls:
                    if self._stop_check():
                        yield json.dumps({"type": "final", "data": "Investigație oprită de utilizator.", "citations": self.citations})
                        return
                    # Normalize tool name: strip whitespace and convert to uppercase for comparison
                    t_name_raw = tc["function"]["name"]
                    t_name_stripped = t_name_raw.strip()
                    t_name_upper = t_name_stripped.upper()
                    
                    # Map normalized names back to original case-sensitive names
                    tool_name_map = {
                        "INSPECT_FORENSIC_LEDGER": "INSPECT_FORENSIC_LEDGER",
                        "SEARCH_TEXT": "SEARCH_TEXT",
                        "SEARCH_STRUCTURED_DATA": "SEARCH_STRUCTURED_DATA", 
                        "FETCH_FULL_DOCUMENT": "FETCH_FULL_DOCUMENT",
                        "GET_DOCUMENT_OUTLINE": "GET_DOCUMENT_OUTLINE",
                        "EXPLORE_GRAPH": "EXPLORE_GRAPH",
                        "TIMELINE": "TIMELINE",
                        "CALCULATE": "CALCULATE",
                        "DETECT_FINANCIAL_ANOMALIES": "DETECT_FINANCIAL_ANOMALIES",
                        "ROLLING_SCRATCHPAD_AUDIT": "ROLLING_SCRATCHPAD_AUDIT"
                    }
                    
                    # First try exact match
                    t_name_normalized = tool_name_map.get(t_name_upper, t_name_stripped)
                    
                    # If still not found, try partial matching (e.g., "search" matches "SEARCH_TEXT")
                    if t_name_normalized == t_name_stripped:
                        for expected_name in tool_name_map.values():
                            if expected_name.startswith(t_name_upper) or t_name_upper in expected_name:
                                t_name_normalized = expected_name
                                break
                    
                    # Handle concatenated tool names (e.g., "SEARCH_TEXTSEARCH_STRUCTURED_DATA")
                    if t_name_normalized == t_name_stripped and len(t_name_stripped) > 20:
                        for expected_name in tool_name_map.values():
                            if t_name_stripped.startswith(expected_name):
                                t_name_normalized = expected_name
                                break
                    
                    # If still not found, try to split concatenated names
                    split_names = None
                    if t_name_normalized == t_name_stripped:
                        for expected_name in sorted(tool_name_map.values(), key=len, reverse=True):
                            remaining = t_name_stripped[len(expected_name):]
                            if remaining and remaining in tool_name_map.values():
                                # This is a concatenated name - split into separate tool calls
                                print(f"[TOOL_DEBUG] Found concatenated tool names: {t_name_stripped}")
                                print(f"[TOOL_DEBUG] Splitting into: {expected_name} and {remaining}")
                                split_names = [expected_name, remaining]
                                
                                # Create a new tool call for the remaining tool
                                new_tc = tc.copy()
                                new_tc["function"]["name"] = remaining
                                # Keep same arguments, just split the call
                                tool_calls.insert(tool_calls.index(tc) + 1, new_tc)
                                
                                t_name_normalized = expected_name
                                break
                    
                    # Extract tool arguments
                    t_args = tc["function"]["arguments"]
                    
                    if t_name_normalized == "SEARCH_TEXT":
                        has_used_search_text = True
                    
                    if isinstance(t_args, str):
                        try:
                            t_args = json.loads(t_args)
                        except:
                            t_args = {"subject": t_args, "concept": t_args, "query": t_args, "entity": t_args, "expression": t_args}
                            
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

                    debug_logger.tool_normalized(
                        original_name=t_name_raw,
                        normalized_name=t_name_normalized,
                        args=t_args if isinstance(t_args, dict) else {"raw": str(t_args)},
                        split_calls=split_names,
                        trace_id=str(self.case_id)
                    )
                                    
                    yield json.dumps({"type": "tool_call", "tool": t_name_raw.strip(), "params": str(t_args)})

                    # Înregistrăm termenul de căutare pentru gardianul anti-surrender
                    if t_name_normalized in ("SEARCH_TEXT", "INSPECT_FORENSIC_LEDGER", "SEARCH_STRUCTURED_DATA", "FETCH_FULL_DOCUMENT"):
                        q_val = ""
                        if isinstance(t_args, dict):
                            q_val = str(t_args.get("concept") or t_args.get("query") or t_args.get("subject") or t_args.get("focus_terms") or "")
                        elif isinstance(t_args, str):
                            q_val = str(t_args)
                        if q_val:
                            self.searched_queries.append(q_val)
                    
                    observation = ""
                    t_exec_start = time.time()
                    exec_success = True
                    exec_err = None
                    try:
                        if t_name_normalized == "INSPECT_FORENSIC_LEDGER":
                            observation = self.tool_inspect_forensic_ledger(
                                query=t_args.get("query", "") if isinstance(t_args, dict) else str(t_args),
                                doc_id=int(t_args.get("doc_id", 0)) if isinstance(t_args, dict) and t_args.get("doc_id") else 0
                            )
                        elif t_name_normalized == "SEARCH_STRUCTURED_DATA":
                            observation = self.tool_search_transactions(
                                subject=t_args.get("subject", "") if isinstance(t_args, dict) else "", 
                                date_filter=t_args.get("date_filter", "") if isinstance(t_args, dict) else "",
                                match_pattern=t_args.get("match_pattern", "") if isinstance(t_args, dict) else "",
                                aggregate=t_args.get("aggregate", False) if isinstance(t_args, dict) else False,
                                limit=int(t_args.get("limit", 30)) if isinstance(t_args, dict) and t_args.get("limit") is not None else 30
                            )
                        elif t_name_normalized == "SEARCH_TEXT":
                            observation = self.tool_search_text(
                                query=t_args.get("concept", "") if isinstance(t_args, dict) else str(t_args),
                                semantic_intent=t_args.get("semantic_intent", "") if isinstance(t_args, dict) else "",
                                doc_id=int(t_args.get("doc_id", 0)) if isinstance(t_args, dict) and t_args.get("doc_id") else 0,
                                page_start=int(t_args.get("page_start", 0)) if isinstance(t_args, dict) and t_args.get("page_start") else 0,
                                page_end=int(t_args.get("page_end", 0)) if isinstance(t_args, dict) and t_args.get("page_end") else 0
                            )
                        elif t_name_normalized == "ROLLING_SCRATCHPAD_AUDIT":
                            t_doc_id = int(t_args.get("doc_id", 0)) if isinstance(t_args, dict) else 0
                            t_focus = (t_args.get("focus_query") or t_args.get("focus_terms") or self.user_question) if isinstance(t_args, dict) else self.user_question
                            for status_msg, is_final, final_obs in self.run_rolling_scratchpad_digest(t_doc_id, t_focus):
                                yield json.dumps({"type": "observation", "data": status_msg})
                                if is_final:
                                    observation = final_obs
                        elif t_name_normalized == "FETCH_FULL_DOCUMENT":
                            t_doc_id = int(t_args.get("doc_id", 0)) if isinstance(t_args, dict) else 0
                            t_focus = (t_args.get("focus_terms") or self.user_question) if isinstance(t_args, dict) else ""
                            with SessionLocal() as db_chk:
                                d_chk = db_chk.query(Document).filter(Document.id == t_doc_id).first()
                                d_len = len(d_chk.raw_text or "") if d_chk else 0
                            budget = self._get_context_budget()
                            if d_len > budget["doc_context_limit"]:
                                for status_msg, is_final, final_obs in self.run_rolling_scratchpad_digest(t_doc_id, t_focus):
                                    yield json.dumps({"type": "observation", "data": status_msg})
                                    if is_final:
                                        observation = final_obs
                            else:
                                observation = self.tool_fetch_full_document(doc_id=t_doc_id, focus_terms=t_focus)
                        elif t_name_normalized == "GET_DOCUMENT_OUTLINE":
                            t_doc_id = int(t_args.get("doc_id", 0)) if isinstance(t_args, dict) else 0
                            observation = self.tool_get_document_outline(doc_id=t_doc_id)
                        elif t_name_normalized == "EXPLORE_GRAPH":
                            observation = self.tool_explore_graph(t_args.get("entity", ""))
                        elif t_name_normalized == "TIMELINE":
                            observation = self.tool_timeline(t_args.get("entity", ""))
                        elif t_name_normalized == "CALCULATE":
                            observation = self.tool_calculate(t_args.get("expression", ""))
                        elif t_name_normalized == "DETECT_FINANCIAL_ANOMALIES":
                            from .anomaly_service import anomaly_service
                            with SessionLocal() as db:
                                res = anomaly_service.analyze_case(self.case_id, db)
                                observation = json.dumps(res, indent=2, ensure_ascii=False)
                        else:
                            # Log unknown tool for debugging
                            logger.warning(f"Unknown tool called: {t_name_raw.strip()} (normalized: {t_name_normalized})")
                            observation = f"Tool '{t_name_raw.strip()}' is not recognized. Available tools: SEARCH_TEXT, SEARCH_STRUCTURED_DATA, FETCH_FULL_DOCUMENT, GET_DOCUMENT_OUTLINE, EXPLORE_GRAPH, TIMELINE, CALCULATE, DETECT_FINANCIAL_ANOMALIES, ROLLING_SCRATCHPAD_AUDIT."
                    except ChatStoppedError:
                        yield json.dumps({"type": "final", "data": "Investigație oprită de utilizator.", "citations": self.citations})
                        return
                    except Exception as e:
                        exec_success = False
                        exec_err = str(e)
                        observation = f"Eroare la executarea tool-ului {t_name_raw.strip()}: {str(e)}"
                    finally:
                        t_exec_dur = (time.time() - t_exec_start) * 1000
                        debug_logger.tool_exec(
                            tool_name=t_name_normalized,
                            duration_ms=t_exec_dur,
                            success=exec_success,
                            obs_len=len(observation),
                            error=exec_err,
                            trace_id=str(self.case_id)
                        )
                    
                    yield json.dumps({"type": "observation", "data": observation[:2500]})
                    
                    tool_msg = {
                        "role": "tool",
                        "content": observation[:3500] if len(observation) > 3500 else observation
                    }
                    if tc.get("id"):
                        tool_msg["tool_call_id"] = tc["id"]
                    messages.append(tool_msg)
                
                # Add a prompt for the model to process the tool results
                messages.append({
                    "role": "user",
                    "content": "Mulțumesc pentru rezultatele instrumentelor. Te rog analizează observațiile și continuă investigația sau oferă un răspuns final bazat pe dovezile găsite."
                })
                
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
            
            # 1. ANTI-SURRENDER FORENSIC GUARD:
            # Detectăm dacă modelul încearcă să declare că lipsesc dovezi / nu există documente înainte de a căuta toți termenii cheie
            surrender_phrases = [
                "nu există", "nu au fost găsite", "nu a fost găsit", "lipsesc dovezi", 
                "imposibilă determinarea", "nu cuprind tranzacția", "nu există dovezi", 
                "nu pot furniza", "nu conțin niciun document", "nu conțin referință",
                "nu menționează", "nu este disponibilă în dozele", "nu este disponibilă în dovezile",
                "nu conține informație despre", "nu conțin informație despre"
            ]
            is_surrender = any(phrase in final_content.lower() for phrase in surrender_phrases)
            unsearched_terms = self._extract_unsearched_key_terms()

            if is_surrender and step < 5 and (not has_used_tools or unsearched_terms):
                if unsearched_terms:
                    prompt_reminder = (
                        f"FORENSIC DIRECTIVE: Ai declarat că lipsesc dovezi sau că nu există informații pentru una dintre cerințe, "
                        f"însă nu ai efectuat căutări pentru toți termenii sau entitățile din întrebare: {', '.join(unsearched_terms[:4])}. "
                        f"Apelează SEARCH_TEXT dedicat pentru fiecare dintre acești termeni înainte de a concluziona."
                    )
                else:
                    prompt_reminder = (
                        f"FORENSIC DIRECTIVE: Do NOT conclude that records are missing without having searched first. "
                        f"Call INSPECT_FORENSIC_LEDGER or SEARCH_TEXT for the specific subjects and entities in the question: '{self.user_question}'."
                    )
                messages.append({
                    "role": "user", 
                    "content": prompt_reminder
                })
                continue

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
            
            # Fallback: If model is struggling, suggest ROLLING_SCRATCHPAD_AUDIT for comprehensive document analysis
            if has_used_tools and step >= 4 and not final_content:
                messages.append({
                    "role": "user", 
                    "content": "⚠️ LOW CONFIDENCE DETECTED: Your previous searches did not yield sufficient evidence. You MUST use ROLLING_SCRATCHPAD_AUDIT to analyze entire documents comprehensively. This tool traverses 100% of text and builds complete forensic understanding without missing any sections."
                })
                continue
                
            if final_content and has_used_tools:
                yield json.dumps({"type": "final", "data": final_content, "citations": self.citations})
                return

        yield json.dumps({"type": "final", "data": "Am atins limita de 15 pași de investigație. Rezumat parțial bazat pe dovezile găsite:", "citations": self.citations})

def truncate_messages(messages: List[Dict], max_messages: int = 12) -> List[Dict]:
    """Truncate message history to keep only recent messages while preserving system prompt."""
    if len(messages) <= max_messages:
        return messages
    
    # Keep system prompt (first message) and last max_messages-1 user/assistant pairs
    system_msg = messages[0] if messages and messages[0].get("role") == "system" else None
    recent_msgs = messages[-(max_messages - 1):] if system_msg else messages[-max_messages:]
    
    return [system_msg] + recent_msgs if system_msg else recent_msgs


def query_investigator(case_id: int, user_question: str):
    agent = AgenticInvestigator(case_id, user_question)
    full_text = ""
    for chunk_json in agent.run():
        chunk = json.loads(chunk_json)
        if chunk.get("type") == "final": 
            full_text = chunk["data"]
            break
    return {"answer": full_text, "citations": agent.citations}
