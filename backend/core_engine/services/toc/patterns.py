"""
Pattern-uri regex și utilitare de normalizare pentru structuri documentare juridice și administrative românești.
Suportă diacritice, variații de majuscule/minuscule și abrevieri standard.
"""

import re
from typing import Optional, Tuple

# Capitole / Părți cu cifre romane sau arabe
RE_CHAPTER = re.compile(
    r"(?i)^[ \t]*(?:capitolul|cap\.)\s*([IVXLCDM]+|[0-9]+)(?:[:.\s-]+(.*))?$",
    re.MULTILINE
)

# Articole și sub-articole (ex: Art. 4, Articolul 4.1.2)
RE_ARTICLE = re.compile(
    r"(?i)^[ \t]*(?:articolul|art\.)\s*(\d+(?:\.\d+)*)(?:[:.\s-]+(.*))?$",
    re.MULTILINE
)

# Anexe și Acte adiționale
RE_ANNEX = re.compile(
    r"(?i)^[ \t]*(?:anexa|act\s+adi[țt]ional)\s*(?:nr\.\s*)?([0-9IVXLCDM]+|[a-z])(?:[:.\s-]+(.*))?$",
    re.MULTILINE
)

# Secțiuni / Părți / Titluri
RE_SECTION = re.compile(
    r"(?i)^[ \t]*(?:sec[țt]iunea|sec[țt]\.|partea|titlul)\s*([0-9IVXLCDM]+)(?:[:.\s-]+(.*))?$",
    re.MULTILINE
)

# Procese verbale, tichete de cântar, facturi, chitanțe
RE_ADMIN_DOC = re.compile(
    r"(?i)^[ \t]*(?:proces[- ]verbal(?:\s+de\s+recep[țt]ie)?|p\.?v\.?|tichet(?:\s+c[âa]ntar)?|factur[aă]|chitan[țt][aă])\s*(?:nr\.\s*)?([0-9A-Z/\-_]+)(?:[:.\s-]+(.*))?$",
    re.MULTILINE
)

# Markdown headings (#, ##, ###)
RE_MARKDOWN_HEADING = re.compile(
    r"^(#{1,6})\s+(.+)$",
    re.MULTILINE
)

# Pattern generic de pagină în text
RE_PAGE_BOUNDARY = re.compile(
    r"(?:<!--\s*PAGE:\s*(\d+)\s*-->|---\s*Page\s*(\d+)\s*---|\f)",
    re.IGNORECASE
)


def classify_and_normalize_heading(raw_line: str) -> Optional[Tuple[str, int, str, str]]:
    """
    Analizează o linie de text și verifică dacă se potrivește cu un tip de antet juridic / administrativ.
    
    Returnează:
        (category, level, normalized_title, id_suffix) sau None dacă nu e antet.
    """
    line = raw_line.strip()
    if not line or len(line) < 3:
        return None

    # Curățare caractere markdown de început (#)
    md_match = RE_MARKDOWN_HEADING.match(line)
    md_level = len(md_match.group(1)) if md_match else 0
    clean_line = md_match.group(2).strip() if md_match else line

    # 1. Capitol
    ch_m = RE_CHAPTER.match(clean_line)
    if ch_m:
        num = ch_m.group(1).upper()
        rest = (ch_m.group(2) or "").strip()
        title = f"Capitolul {num}: {rest}" if rest else f"Capitolul {num}"
        return ("chapter", 1, title, f"cap_{num.lower()}")

    # 2. Secțiune / Partea / Titlu
    sec_m = RE_SECTION.match(clean_line)
    if sec_m:
        num = sec_m.group(1).upper()
        rest = (sec_m.group(2) or "").strip()
        title = f"Secțiunea {num}: {rest}" if rest else f"Secțiunea {num}"
        return ("section", 1, title, f"sec_{num.lower()}")

    # 3. Anexă / Act adițional
    ann_m = RE_ANNEX.match(clean_line)
    if ann_m:
        num = ann_m.group(1).upper()
        rest = (ann_m.group(2) or "").strip()
        title = f"Anexa {num}: {rest}" if rest else f"Anexa {num}"
        return ("annex", 1, title, f"anexa_{num.lower()}")

    # 4. Proces-verbal / Tichet cântar / Factură
    adm_m = RE_ADMIN_DOC.match(clean_line)
    if adm_m:
        code = adm_m.group(1).strip()
        rest = (adm_m.group(2) or "").strip()
        title = f"Act administrativ nr. {code}: {rest}" if rest else f"Act administrativ nr. {code}"
        return ("minute", 2, title, f"act_{code.lower().replace('/', '_')}")

    # 5. Articol
    art_m = RE_ARTICLE.match(clean_line)
    if art_m:
        num = art_m.group(1).strip()
        rest = (art_m.group(2) or "").strip()
        title = f"Articolul {num}: {rest}" if rest else f"Articolul {num}"
        level = 3 if "." in num else 2
        return ("article", level, title, f"art_{num.replace('.', '_')}")

    # 6. Dacă e explicit markdown heading (#, ##, ###) cu text consistent
    if md_level > 0 and len(clean_line) <= 120:
        # Nu e doar o propoziție lungă cu #
        cat = "chapter" if md_level == 1 else ("section" if md_level == 2 else "clause")
        return (cat, min(md_level, 3), clean_line, f"h_{abs(hash(clean_line)) % 100000}")

    # 7. Titluri cu majuscule (ALL CAPS) scurte, tipice pentru contracte românești
    if clean_line.isupper() and 5 <= len(clean_line) <= 60 and not clean_line.endswith((".", ",")):
        return ("section", 2, clean_line.title(), f"sec_{abs(hash(clean_line)) % 100000}")

    return None
