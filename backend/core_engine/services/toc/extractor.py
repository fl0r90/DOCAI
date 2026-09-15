"""
Extractor euristic de antete și structură ierarhică (TOCExtractor).
Analizează textul brut / markdown, detectează delimitatorii de pagină
și extrage candidații structurali cu snippet-uri și pagini de referință.
"""

import re
from typing import List, Dict, Any, Optional
from .schemas import TOCItem, DocumentTOC
from .patterns import classify_and_normalize_heading, RE_PAGE_BOUNDARY


class TOCExtractor:
    """Extrage candidații de cuprins din text/markdown cu granularitate de pagină."""

    def __init__(self, raw_text: str, document_id: Optional[int] = None, document_title: Optional[str] = None):
        self.raw_text = raw_text or ""
        self.document_id = document_id
        self.document_title = document_title

    def extract_candidates(self) -> List[Dict[str, Any]]:
        """
        Scanează textul linie cu linie, ținând cont de markerii de pagină.
        Returnează o listă liniară de elemente detectate.
        """
        candidates: List[Dict[str, Any]] = []
        current_page = 1
        lines = self.raw_text.splitlines()

        current_heading: Optional[Dict[str, Any]] = None
        current_body_lines: List[str] = []

        def flush_heading():
            nonlocal current_heading, current_body_lines
            if current_heading:
                body = " ".join([l.strip() for l in current_body_lines if l.strip()])
                current_heading["snippet"] = body[:200] if body else None
                candidates.append(current_heading)
                current_heading = None
                current_body_lines = []

        for line in lines:
            # 1. Verificare delimitator de pagină
            page_m = RE_PAGE_BOUNDARY.search(line)
            if page_m:
                new_page_str = page_m.group(1) or page_m.group(2)
                if new_page_str and new_page_str.isdigit():
                    current_page = int(new_page_str)
                else:
                    current_page += 1
                continue

            # 2. Verificare linie dacă e antet
            classification = classify_and_normalize_heading(line)
            if classification:
                flush_heading()
                cat, level, norm_title, id_suffix = classification
                current_heading = {
                    "id": f"{id_suffix}_{len(candidates)+1}",
                    "level": level,
                    "title": line.strip(),
                    "normalized_title": norm_title,
                    "category": cat,
                    "page_start": current_page,
                    "page_end": current_page,
                    "snippet": None,
                }
            else:
                if current_heading and len(current_body_lines) < 10:
                    current_body_lines.append(line)

        flush_heading()

        # Calculare automată a page_end pentru fiecare secțiune (până la secțiunea următoare)
        for i in range(len(candidates)):
            if i + 1 < len(candidates):
                next_page = candidates[i + 1]["page_start"]
                candidates[i]["page_end"] = max(candidates[i]["page_start"], next_page)
            else:
                candidates[i]["page_end"] = max(candidates[i]["page_start"], current_page)

        return candidates

    def build_heuristic_tree(self, candidates: List[Dict[str, Any]], total_pages: int) -> DocumentTOC:
        """
        Construiește un arbore ierarhic Pydantic (DocumentTOC) pe baza nivelurilor (level 1, 2, 3)
        fără a apela un LLM (servind ca fallback ultra-rapid).
        """
        root_items: List[TOCItem] = []
        stack: List[TOCItem] = []

        for cand in candidates:
            item = TOCItem(
                id=cand["id"],
                level=cand["level"],
                title=cand["title"],
                normalized_title=cand["normalized_title"],
                category=cand["category"],
                page_start=cand["page_start"],
                page_end=cand.get("page_end"),
                snippet=cand.get("snippet"),
                children=[]
            )

            # Ajustare stivă în funcție de nivel
            while stack and stack[-1].level >= item.level:
                stack.pop()

            if stack:
                stack[-1].children.append(item)
            else:
                root_items.append(item)

            stack.append(item)

        return DocumentTOC(
            document_id=self.document_id,
            document_title=self.document_title,
            total_pages=total_pages,
            total_sections=len(candidates),
            items=root_items,
            raw_headings_count=len(candidates)
        )
