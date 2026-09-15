"""
Serviciul principal de orchestrare TOC (TOCService).
Lipește extracția euristică, îmbogățirea prin LLM și persistența în baza de date PostgreSQL.
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from .schemas import DocumentTOC
from .extractor import TOCExtractor
from .enricher import TOCLLMEnricher
from ...models import Document

logger = logging.getLogger(__name__)


class TOCService:
    """Orchestrator pentru generarea și gestionarea cuprinsului criminalistic."""

    def __init__(self, model_override: Optional[str] = None):
        self.model_override = model_override
        self.enricher = TOCLLMEnricher(model_override=model_override)

    def generate_toc(
        self,
        raw_text: str,
        total_pages: int = 1,
        document_id: Optional[int] = None,
        document_title: Optional[str] = None,
        use_llm: bool = True
    ) -> DocumentTOC:
        """
        Generează un DocumentTOC complet din textul brut / markdown al documentului.
        
        Pași:
        1. Extragere euristică a candidaților și a delimitatorilor de pagină.
        2. Construire arbore structural de rezervă (heuristic).
        3. (Opțional) Rafinare și ierarhizare prin LLM cu cădere sigură pe arborele euristic.
        """
        extractor = TOCExtractor(
            raw_text=raw_text,
            document_id=document_id,
            document_title=document_title
        )
        candidates = extractor.extract_candidates()
        heuristic_toc = extractor.build_heuristic_tree(candidates, total_pages=total_pages)

        if not use_llm or not candidates:
            return heuristic_toc

        try:
            return self.enricher.enrich_toc(
                candidates=candidates,
                total_pages=total_pages,
                document_id=document_id,
                document_title=document_title,
                fallback_toc=heuristic_toc
            )
        except Exception as e:
            logger.warning(f"[TOC_SERVICE] Eșec îmbogățire LLM, folosim arborele euristic: {e}")
            return heuristic_toc

    def save_toc_to_db(self, db: Session, doc_id: int, toc: DocumentTOC) -> bool:
        """Salvează cuprinsul în coloana doc_metadata a documentului din PostgreSQL."""
        try:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                logger.error(f"[TOC_SERVICE] Documentul cu ID-ul {doc_id} nu a fost găsit în baza de date.")
                return False

            meta = dict(doc.doc_metadata or {})
            meta["toc"] = toc.model_dump()
            meta["outline"] = toc.to_flat_list()
            doc.doc_metadata = meta
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"[TOC_SERVICE] Eroare la salvarea TOC în DB pentru doc {doc_id}: {e}")
            return False

    def get_toc_from_db(self, db: Session, doc_id: int) -> Optional[DocumentTOC]:
        """Încarcă cuprinsul unui document din baza de date."""
        try:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if not doc or not doc.doc_metadata:
                return None
            toc_data = doc.doc_metadata.get("toc")
            if toc_data:
                return DocumentTOC(**toc_data)
            return None
        except Exception as e:
            logger.error(f"[TOC_SERVICE] Eroare la citirea TOC pentru doc {doc_id}: {e}")
            return None


toc_service = TOCService()
