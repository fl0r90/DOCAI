from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class TOCItem(BaseModel):
    """Reprezintă un nod / o secțiune structurală în cuprinsul criminalistic al documentului."""
    id: str = Field(..., description="Identificator unic al secțiunii (ex: cap_1, art_4_1)")
    level: int = Field(default=1, description="Nivelul ierarhic: 1=Capitol/Parte, 2=Articol/Secțiune, 3=Paragraf/Sub-clauză")
    title: str = Field(..., description="Titlul brut extras din document")
    normalized_title: str = Field(..., description="Titlul standardizat (ex: Capitolul I: Dispoziții Generale, Articolul 4: Obligații)")
    category: str = Field(
        default="section",
        description="Categoria: chapter | article | annex | minute | scale_ticket | invoice | section | other"
    )
    page_start: int = Field(default=1, description="Pagina de început a secțiunii (1-indexed)")
    page_end: Optional[int] = Field(default=None, description="Pagina de sfârșit a secțiunii")
    snippet: Optional[str] = Field(default=None, description="Primele 150-250 de caractere din corpul secțiunii")
    children: List[TOCItem] = Field(default_factory=list, description="Subsecțiuni / clauze subordonate")


class DocumentTOC(BaseModel):
    """Cuprins structural criminalistic de înaltă densitate (Deep Forensic Document Outline)."""
    document_id: Optional[int] = Field(default=None, description="ID-ul documentului din baza de date")
    document_title: Optional[str] = Field(default=None, description="Titlul documentului sau numele fișierului")
    total_pages: int = Field(default=1, description="Numărul total de pagini")
    total_sections: int = Field(default=0, description="Numărul total de secțiuni identificate")
    items: List[TOCItem] = Field(default_factory=list, description="Lista arborescentă a secțiunilor principale")
    raw_headings_count: int = Field(default=0, description="Numărul de titluri brute detectate prin euristici/regex")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_flat_list(self) -> List[Dict[str, Any]]:
        """Returnează o listă liniară a tuturor secțiunilor (util pentru căutare rapidă de către agent)."""
        flat = []

        def _traverse(node: TOCItem, path: str = ""):
            current_path = f"{path} > {node.normalized_title}" if path else node.normalized_title
            flat.append({
                "id": node.id,
                "level": node.level,
                "title": node.normalized_title,
                "category": node.category,
                "path": current_path,
                "page_start": node.page_start,
                "page_end": node.page_end or node.page_start,
                "snippet": node.snippet
            })
            for child in node.children:
                _traverse(child, current_path)

        for item in self.items:
            _traverse(item)
        return flat

    def to_readable_text(self) -> str:
        """Randează cuprinsul într-un format text concis și lizibil pentru prompt-ul LLM."""
        lines = [f"=== CUPRINS STRUCTURAL (Total pagini: {self.total_pages}) ==="]

        def _format_node(node: TOCItem, indent: int = 0):
            prefix = "  " * indent
            page_info = f"[Pag. {node.page_start}]" if not node.page_end or node.page_end == node.page_start else f"[Pag. {node.page_start}-{node.page_end}]"
            lines.append(f"{prefix}• {page_info} {node.normalized_title}")
            for child in node.children:
                _format_node(child, indent + 1)

        for item in self.items:
            _format_node(item)
        return "\n".join(lines)
