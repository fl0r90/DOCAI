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
        self.working_memory = {}
        self.evidence_cache = {}
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

    def _generate_investigation_plan(self) -> List[Dict[str, Any]]:
        """Decompune semantic întrebarea utilizatorului în 1-4 obiective atomice folosind LLM cu fallback determinist."""
        plan_prompt = (
            "You are a Senior Forensic Data Auditor. Decompose the user inquiry into 1 to 4 distinct atomic verification targets.\n"
            "For each target, identify:\n"
            "- id: sequential integer (1, 2, ...)\n"
            "- title: short description of what must be verified\n"
            "- keys: 1 to 3 specific exact identifiers (document/invoice codes, person names, technical terms, channels like WhatsApp)\n\n"
            "Output ONLY valid JSON matching this schema:\n"
            "{\"targets\": [{\"id\": 1, \"title\": \"...\", \"keys\": [\"...\"]}]}\n\n"
            f"USER INQUIRY: {self.user_question}"
        )
        try:
            res = UnifiedLLMClient.chat_step(
                messages=[
                    {"role": "system", "content": "You are a Forensic Planning Engine. Output strictly valid JSON."},
                    {"role": "user", "content": plan_prompt}
                ],
                model=self.active_model,
                temperature=0.0,
                num_ctx=4096,
                stop_check=self._stop_check
            )
            content = res.get("content", "").strip()
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                targets = parsed.get("targets", [])
                if targets and isinstance(targets, list):
                    clean_targets = []
                    for idx, t in enumerate(targets, 1):
                        keys = [str(k).strip() for k in t.get("keys", []) if str(k).strip()]
                        clean_targets.append({
                            "id": idx,
                            "title": t.get("title", f"Obiectiv {idx}"),
                            "keys": keys or [t.get("title", f"Obiectiv {idx}")[:40]]
                        })
                    if clean_targets:
                        return clean_targets
        except Exception as e:
            print(f"[!] Plan generation via LLM fallback to heuristic: {e}")

        # Fallback dacă LLM-ul nu a răspuns în JSON:
        sub_qs = decompose_question(self.user_question)
        unsearched = self._extract_unsearched_key_terms()
        clean_targets = []
        for idx, sq in enumerate(sub_qs, 1):
            matching_keys = [k for k in unsearched if k.lower() in sq.lower()]
            if not matching_keys and idx <= len(unsearched):
                matching_keys = [unsearched[idx - 1]]
            clean_targets.append({
                "id": idx,
                "title": sq,
                "keys": matching_keys or [sq[:50]]
            })
        return clean_targets

    def _execute_sub_target(self, target: Dict[str, Any]) -> str:
        """Rezolvă un target individual într-un context izolat și curat (Context-Flush)."""
        evidence_snippets = []
        keys_to_search = target.get("keys", []) or []
        for k in keys_to_search:
            if self._stop_check():
                raise ChatStoppedError("Stop request received during sub-target.")
            obs = self.tool_search_text(k)
            if obs and "No text fragments found" not in obs and "No valid keywords" not in obs:
                evidence_snippets.append(obs)
                self.searched_queries.append(k)

        # Dacă nu s-au găsit fragmente relevante prin chei, încercăm cu titlul targetului
        if not evidence_snippets:
            obs = self.tool_search_text(target["title"])
            if obs and "No text fragments found" not in obs:
                evidence_snippets.append(obs)
                self.searched_queries.append(target["title"])

        combined_evidence = "\n\n".join(evidence_snippets)
        if not combined_evidence:
            combined_evidence = "Nu s-au identificat fragmente relevante în dosar pentru acest criteriu."

        # Informații contextuale suplimentare din working memory precedent (pentru calcule dependente)
        prev_facts_ctx = ""
        if self.working_memory:
            prev_facts_ctx = "DATE PRECEDENTE DEJA CONFIRMATE ÎN INVESTIGAȚIE:\n" + "\n".join([
                f"- Ținta {tid}: {fact}" for tid, fact in self.working_memory.items()
            ]) + "\n\n"

        prompt = (
            f"OBIECTIV DE INVESTIGAT: {target['title']}\n\n"
            f"{prev_facts_ctx}"
            f"DOVEZI IDENTIFICATE DIN DOSAR:\n{combined_evidence[:8000]}\n\n"
            "CERINȚĂ: Formulează concluzia factuală concretă pentru acest obiectiv în limba ROMÂNĂ. "
            "Extrage cifre exacte, cantități, diferențe și citează obligatoriu referințele [REF x]. "
            "Efectuează calcule matematice directe dacă obiectivul cere o diferență sau o valoare. "
            "Dacă dovezile nu conțin nicio mențiune sau document despre acest obiectiv, specifică explicit 'Nu s-au găsit dovezi'."
        )

        step_res = UnifiedLLMClient.chat_step(
            messages=[
                {"role": "system", "content": "You are a Forensic Evidence Auditor. Answer strictly using the provided citations in ROMANIAN. Be concise, rigorous, and direct (2-4 sentences)."},
                {"role": "user", "content": prompt}
            ],
            model=self.active_model,
            temperature=0.0,
            num_ctx=4096,
            stop_check=self._stop_check
        )
        return step_res.get("content", "").strip()

    def _synthesize_final_report(self, plan: List[Dict[str, Any]]) -> str:
        """Generează raportul final unificat din faptele verificate per target."""
        facts_summary = "\n\n".join([
            f"### Ținta {t['id']}: {t['title']}\n{self.working_memory.get(t['id'], 'Lipsesc dovezi.')}"
            for t in plan
        ])

        final_prompt = (
            f"ÎNTREBAREA INVESTIGATĂ:\n{self.user_question}\n\n"
            f"CONCLUZII ȘI FAPTE VERIFICATE PE OBIECTIVE:\n{facts_summary}\n\n"
            "Redactează raportul final unificat în limba ROMÂNĂ conform formatului criminalistic standard:\n"
            "[FACTS]\n"
            "- Listă detaliată a tuturor faptelor confirmate, cantităților și participanților, citând referințele [x]\n"
            "[ANALYSIS]\n"
            "- Conexiuni logice între documente, contradicții identificate (ex: discrepanțe între acte formale și discuții informale)\n"
            "[CONCLUSION]\n"
            "- Răspunsul direct, clar și complet la fiecare aspect din întrebarea utilizatorului\n"
            "[MISSING EVIDENCE]\n"
            "- Ce date lipsesc efectiv, sau 'N/A'\n"
            "[CONFIDENCE]: HIGH"
        )

        final_res = UnifiedLLMClient.chat_step(
            messages=[
                {"role": "system", "content": "You are a Master Forensic Auditor. Synthesize verified evidence into a professional forensic report in ROMANIAN."},
                {"role": "user", "content": final_prompt}
            ],
            model=self.active_model,
            temperature=0.0,
            num_ctx=6144,
            stop_check=self._stop_check
        )
        return final_res.get("content", "").strip()

    def run(self):
        yield json.dumps({"type": "status", "data": "Forensic Agent is thinking..."})
        if self._stop_check():
            yield json.dumps({"type": "final", "data": "Investigație oprită de utilizator.", "citations": self.citations})
            return

        # 1. Pasul 0: Planificare Semantică Agnostică
        yield json.dumps({"type": "step", "data": "Etapa 1: Stabilire plan de investigație..."})
        plan = self._generate_investigation_plan()
        titles_str = "; ".join(f"[{t['id']}] {t['title']}" for t in plan)
        yield json.dumps({"type": "observation", "data": f"Plan investigație aprobat ({len(plan)} obiective): {titles_str}"})

        # 2. Execuție Secvențială pe Ținte cu Context-Flush
        for target in plan:
            if self._stop_check():
                yield json.dumps({"type": "final", "data": "Investigație oprită de utilizator.", "citations": self.citations})
                return

            yield json.dumps({"type": "step", "data": f"Investigare Ținta {target['id']}/{len(plan)}: {target['title']}"})
            try:
                fact_result = self._execute_sub_target(target)
            except ChatStoppedError:
                yield json.dumps({"type": "final", "data": "Investigație oprită de utilizator.", "citations": self.citations})
                return
            except Exception as e:
                fact_result = f"Eroare la analiza țintei: {e}"

            self.working_memory[target["id"]] = fact_result
            yield json.dumps({"type": "observation", "data": f"✓ Ținta {target['id']} finalizată: {fact_result[:300]}..."})

        # 3. Sinteză Finală Verificată
        if self._stop_check():
            yield json.dumps({"type": "final", "data": "Investigație oprită de utilizator.", "citations": self.citations})
            return

        yield json.dumps({"type": "step", "data": "Etapa Finală: Redactare raport de sinteză..."})
        try:
            final_report = self._synthesize_final_report(plan)
        except ChatStoppedError:
            yield json.dumps({"type": "final", "data": "Investigație oprită de utilizator.", "citations": self.citations})
            return
        except Exception as e:
            final_report = f"Eroare la redactarea raportului final: {e}"

        yield json.dumps({"type": "final", "data": final_report, "citations": self.citations})

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
