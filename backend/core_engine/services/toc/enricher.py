"""
Modul de îmbogățire structurală și semantică a cuprinsului prin LLM (TOCLLMEnricher).
Normalizează ierarhia, elimină alertele false și generează o structură strictă JSON.
Include mecanisme de retry, backoff și cădere grațioasă (fallback pe arbore euristic).
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from .schemas import TOCItem, DocumentTOC
from ..llm_client import UnifiedLLMClient

logger = logging.getLogger(__name__)


class TOCLLMEnricher:
    """Rafinează și ierarhizează candidații de cuprins folosind LLM-ul configurat."""

    def __init__(self, model_override: Optional[str] = None):
        self.model_override = model_override

    def enrich_toc(
        self,
        candidates: List[Dict[str, Any]],
        total_pages: int,
        document_id: Optional[int] = None,
        document_title: Optional[str] = None,
        fallback_toc: Optional[DocumentTOC] = None
    ) -> DocumentTOC:
        """
        Trimite lista de candidați către LLM pentru curățare, ierarhizare și validare.
        Dacă LLM-ul eșuează sau returnează JSON invalid, se returnează `fallback_toc`.
        """
        if not candidates:
            return fallback_toc or DocumentTOC(
                document_id=document_id,
                document_title=document_title,
                total_pages=total_pages,
                total_sections=0,
                items=[]
            )

        prompt = self._build_prompt(candidates, document_title, total_pages)
        messages = [
            {
                "role": "system",
                "content": (
                    "Ești un Arhitect de Sisteme Juridice și Criminalistice. "
                    "Rolul tău este să transformi o listă brută de antete detectate într-un CUPRINS STRUCTURAT (TOC) "
                    "ierarhic, curat, cu diacritice și numerotare corectă. "
                    "Răspunde STRICT cu un obiect JSON conform specificației cerute."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        # Reîncercare cu backoff
        for attempt in range(2):
            try:
                res = UnifiedLLMClient.chat_step(
                    messages=messages,
                    model=self.model_override,
                    temperature=0.0
                )
                raw_content = (res.get("content") or "").strip()
                parsed_json = self._extract_json(raw_content)
                if parsed_json and "items" in parsed_json:
                    return self._build_doc_toc(
                        parsed_json=parsed_json,
                        total_pages=total_pages,
                        document_id=document_id,
                        document_title=document_title,
                        raw_count=len(candidates)
                    )
            except Exception as e:
                logger.warning(f"[TOC_ENRICHER] Încercarea {attempt + 1} a eșuat: {e}")

        logger.info("[TOC_ENRICHER] Folosim arborele euristic ca fallback sigur.")
        return fallback_toc or DocumentTOC(
            document_id=document_id,
            document_title=document_title,
            total_pages=total_pages,
            total_sections=len(candidates),
            items=[]
        )

    def _build_prompt(self, candidates: List[Dict[str, Any]], title: Optional[str], total_pages: int) -> str:
        candidates_preview = []
        for c in candidates:
            item_str = f"- [ID: {c['id']}] Pagina {c['page_start']}: \"{c['title']}\" (Tip sugerat: {c['category']}, Nivel: {c['level']})"
            if c.get("snippet"):
                item_str += f" | Text introductiv: {c['snippet'][:120]}..."
            candidates_preview.append(item_str)

        preview_text = "\n".join(candidates_preview)

        return f"""Document analizat: "{title or 'Document necunoscut'}" (Total pagini: {total_pages})

Mai jos este lista antetelor brute extrase prin regex și analiză de text:
{preview_text}

CERINȚE:
1. Elimină antetele false (linii care nu sunt titluri reale de secțiuni, articole sau capitole).
2. Grupează articolele și subsecțiunile în mod ierarhic (ex: Articolele din Capitolul I trebuie să fie în 'children' ale Capitolului I).
3. Păstrează 'page_start' și 'page_end' pentru fiecare element.
4. Răspunde DOAR cu JSON în următorul format:
{{
  "items": [
    {{
      "id": "cap_1",
      "level": 1,
      "title": "Titlu brut",
      "normalized_title": "Capitolul I: Obiectul Contractului",
      "category": "chapter",
      "page_start": 1,
      "page_end": 2,
      "snippet": "...",
      "children": [
        {{
          "id": "art_1",
          "level": 2,
          "title": "Art. 1",
          "normalized_title": "Articolul 1: Părțile Contractante",
          "category": "article",
          "page_start": 1,
          "page_end": 1,
          "snippet": "...",
          "children": []
        }}
      ]
    }}
  ]
}}
"""

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extrage blocul JSON dintr-un răspuns LLM, eliminând eventualele marcaje markdown."""
        if not text:
            return None
        # Căutare bloc ```json ... ```
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
        else:
            # Căutare prima acoladă deschisă și ultima acoladă închisă
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start:end+1]

        try:
            return json.loads(text)
        except Exception:
            return None

    def _build_doc_toc(
        self,
        parsed_json: Dict[str, Any],
        total_pages: int,
        document_id: Optional[int],
        document_title: Optional[str],
        raw_count: int
    ) -> DocumentTOC:
        def parse_node(data: Dict[str, Any]) -> TOCItem:
            children = [parse_node(c) for c in data.get("children", []) if isinstance(c, dict)]
            return TOCItem(
                id=str(data.get("id") or f"node_{abs(hash(str(data))) % 100000}"),
                level=int(data.get("level", 1)),
                title=str(data.get("title") or data.get("normalized_title") or "Secțiune"),
                normalized_title=str(data.get("normalized_title") or data.get("title") or "Secțiune"),
                category=str(data.get("category", "section")),
                page_start=int(data.get("page_start", 1)),
                page_end=int(data.get("page_end")) if data.get("page_end") else None,
                snippet=data.get("snippet"),
                children=children
            )

        root_items = [parse_node(item) for item in parsed_json.get("items", []) if isinstance(item, dict)]

        def count_nodes(items: List[TOCItem]) -> int:
            total = len(items)
            for it in items:
                total += count_nodes(it.children)
            return total

        return DocumentTOC(
            document_id=document_id,
            document_title=document_title,
            total_pages=total_pages,
            total_sections=count_nodes(root_items),
            items=root_items,
            raw_headings_count=raw_count
        )
