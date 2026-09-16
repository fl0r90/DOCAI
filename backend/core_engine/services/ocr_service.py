import os
import io
import base64
from PIL import Image
import fitz  # PyMuPDF
import requests
import pytesseract

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
from docling.datamodel.accelerator_options import AcceleratorOptions
from docling.datamodel.base_models import InputFormat
import time
from .debug_logger import debug_logger

# ==============================================================================
# SINGLETON CONVERTERS (Instanțiate o singură dată per proces, nu la fiecare fișier)
# ==============================================================================
_digital_converter = None
_ocr_converter = None

def _get_digital_converter() -> DocumentConverter:
    """Speed 1: Convertor Docling cu OCR DEZACTIVAT (pentru PDF-uri native digitale).
    Timp de conversie: 1-3 secunde chiar și pentru sute de pagini.
    """
    global _digital_converter
    if _digital_converter is None:
        pipeline_options = PdfPipelineOptions(
            accelerator_options=AcceleratorOptions(num_threads=os.cpu_count())
        )
        pipeline_options.do_ocr = False
        _digital_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
    return _digital_converter

def _get_ocr_converter() -> DocumentConverter:
    """Speed 2: Convertor Docling cu RapidOCR ACTIVAT (pentru PDF-uri scanate).
    Instanțiat ca singleton de proces pentru a evita reîncărcarea modelelor ONNX.
    """
    global _ocr_converter
    if _ocr_converter is None:
        pipeline_options = PdfPipelineOptions(
            accelerator_options=AcceleratorOptions(num_threads=os.cpu_count())
        )
        pipeline_options.do_ocr = True
        pipeline_options.ocr_options = RapidOcrOptions()
        _ocr_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
    return _ocr_converter

def _is_digital_pdf(file_path: str, min_chars_per_page: int = 80, sample_pages: int = 10) -> bool:
    """Verifică rapid cu PyMuPDF dacă documentul PDF are text nativ digital."""
    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        if total_pages == 0:
            return False
        
        pages_to_check = min(total_pages, sample_pages)
        total_chars = 0
        pages_with_text = 0

        for i in range(pages_to_check):
            page_text = doc[i].get_text().strip()
            chars = len(page_text)
            total_chars += chars
            if chars >= min_chars_per_page:
                pages_with_text += 1

        doc.close()

        avg_chars = total_chars / pages_to_check
        return avg_chars >= min_chars_per_page or (pages_with_text / pages_to_check >= 0.7)
    except Exception as e:
        print(f"[!] Verificare digitală PDF eșuată ({e}), fallback la OCR.")
        return False

def _insert_page_markers(md_text: str, page_first_snippets: list) -> str:
    """Insert <!-- PAGE: N --> markers at page boundaries in markdown.
    page_first_snippets: list of (page_no, first_text_snippet) in document order.
    """
    if not page_first_snippets or len(page_first_snippets) <= 1:
        return md_text
    result = md_text
    for page_no, snippet in reversed(page_first_snippets[1:]):
        if not snippet:
            continue
        search = snippet[:60].strip()
        if len(search) < 10:
            search = snippet[:30].strip()
        if not search:
            continue
        idx = result.find(search)
        if idx != -1:
            marker = f"\n<!-- PAGE: {page_no} -->\n"
            result = result[:idx] + marker + result[idx:]
    return result


def _process_with_docling(converter: DocumentConverter, file_path: str) -> dict:
    """Execută conversia via Docling și extrage Markdown, chunks și items structurate."""
    result = converter.convert(file_path)
    md_text = result.document.export_to_markdown()

    chunks = []
    items = []
    page_first_snippets = []
    seen_pages = set()
    for item in result.document.texts:
        page_no = 1
        spatial = ""
        if item.prov:
            p = item.prov[0]
            page_no = getattr(p, 'page_no', 1)
            bbox = getattr(p, 'bbox', None)
            if bbox:
                spatial = f"l={bbox.l},t={bbox.t},r={bbox.r},b={bbox.b}"

        chunks.append({
            "content": item.text,
            "page": page_no,
            "spatial": spatial
        })
        if item.text and item.text.strip():
            items.append({"type": "TEXT", "content": item.text, "page": page_no})
            if page_no not in seen_pages:
                seen_pages.add(page_no)
                page_first_snippets.append((page_no, item.text.strip()))

    for table in getattr(result.document, "tables", []) or []:
        try:
            table_md = table.export_to_markdown()
        except Exception:
            table_md = ""
        if table_md and table_md.strip():
            page_no = 1
            table_spatial = ""
            if getattr(table, "prov", None) and len(table.prov) > 0:
                p = table.prov[0]
                page_no = getattr(p, 'page_no', 1)
                bbox = getattr(p, 'bbox', None)
                if bbox:
                    table_spatial = f"l={bbox.l},t={bbox.t},r={bbox.r},b={bbox.b}"
            items.append({"type": "TABLE", "content": table_md, "page": page_no, "spatial": table_spatial})
            chunks.append({
                "content": table_md,
                "page": page_no,
                "spatial": table_spatial,
                "is_table": True
            })

    md_text = _insert_page_markers(md_text, page_first_snippets)

    return {
        "markdown": md_text,
        "chunks": chunks,
        "items": items
    }

def _process_image_with_vision(image_path: str) -> dict:
    """Speed 3: Transcriere vizuală cu modelul Vision (Gemma 4 / Ollama) pentru imagini
    sau scanări degradate unde OCR-ul clasic eșuează.
    """
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            max_dim = 1024
            if max(img.size) > max_dim:
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        ollama_url = os.getenv("OLLAMA_URL", "http://llm:11434").rstrip("/")
        model_name = os.getenv("VISION_MODEL", "gemma4:e4b")

        payload = {
            "model": model_name,
            "messages": [{
                "role": "user",
                "content": "Transcribe all text from this image accurately into clean GitHub Markdown. Preserve tables, headers, lists, numbers and structure verbatim. Return only the Markdown text without commentary.",
                "images": [img_b64]
            }],
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_ctx": 8192
            }
        }

        resp = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=300)
        resp.raise_for_status()
        data = resp.json()
        md_text = data.get("message", {}).get("content", "").strip()

        if not md_text:
            raise ValueError("Modelul Vision a returnat text gol.")

        chunks = [{"content": md_text, "page": 1, "spatial": ""}]
        items = [{"type": "TEXT", "content": md_text, "page": 1}]

        return {
            "markdown": md_text,
            "chunks": chunks,
            "items": items
        }
    except Exception as e:
        print(f"[!] Vision OCR error for {image_path}: {e}")
        try:
            with Image.open(image_path) as img:
                tess_text = pytesseract.image_to_string(img).strip()
                return {
                    "markdown": tess_text,
                    "chunks": [{"content": tess_text, "page": 1, "spatial": ""}],
                    "items": [{"type": "TEXT", "content": tess_text, "page": 1}]
                }
        except Exception as te:
            return {"error": f"Vision and Tesseract failed: {e}; {te}"}

class OCRService:
    """Clasă compatibilitate legacy."""
    def __init__(self):
        pass

    def _get_converter(self):
        return _get_ocr_converter()

    def process_file(self, file_path: str) -> dict:
        return process_document(file_path)

def process_document(file_path: str) -> dict:
    """
    3-SPEED HYBRID OCR ENGINE (Etapa 29):
      - VITEZA 1: Digital Fast-Path (fitz check -> Docling do_ocr=False). Timp: 1-3s.
      - VITEZA 2: Scanned PDF (Docling + RapidOCR singleton). Timp: 20-50s.
      - VITEZA 3: Pure Images / Degraded (Gemma 4 Vision via Ollama).
    """
    t_ocr_start = time.time()
    try:
        ext = os.path.splitext(file_path)[1].lower()

        # Cazul A: Imagini izolate (.jpg, .jpeg, .png) -> Viteza 3 (Gemma 4 Vision)
        if ext in ('.jpg', '.jpeg', '.png', '.bmp', '.webp'):
            print(f"[⚡ Speed 3 - Vision] Procesare imagine cu Vision AI: {file_path}")
            res = _process_image_with_vision(file_path)
            dur_ms = (time.time() - t_ocr_start) * 1000
            debug_logger.info("ocr_service", "OCR_PROCESS_COMPLETE", data={"file": os.path.basename(file_path), "speed": "Speed3_Vision", "duration_ms": round(dur_ms, 2)})
            return res

        # Cazul B: PDF-uri
        if ext == '.pdf':
            is_digital = _is_digital_pdf(file_path)
            
            if is_digital:
                print(f"[⚡ Speed 1 - Digital Fast-Path] PDF nativ digital detectat. Rulare Docling fără OCR: {file_path}")
                converter = _get_digital_converter()
                res = _process_with_docling(converter, file_path)
                if len(res.get("markdown", "").strip()) >= 50:
                    dur_ms = (time.time() - t_ocr_start) * 1000
                    debug_logger.info("ocr_service", "OCR_PROCESS_COMPLETE", data={"file": os.path.basename(file_path), "speed": "Speed1_Digital", "duration_ms": round(dur_ms, 2), "chars": len(res.get("markdown", ""))})
                    return res
                print("[!] Digital Fast-Path a extras prea puțin text. Trecem la Speed 2 (RapidOCR)...")

            # Viteza 2: PDF scanat cu RapidOCR
            print(f"[⚡ Speed 2 - Scanned OCR] PDF scanat detectat. Rulare Docling + RapidOCR: {file_path}")
            converter = _get_ocr_converter()
            res = _process_with_docling(converter, file_path)

            # Dacă scanarea a fost atât de degradată încât nu s-a extras aproape nimic (<50 caractere)
            # și are un număr rezonabil de pagini (<= 5), încercăm Viteza 3 (Vision pe prima pagină)
            if len(res.get("markdown", "").strip()) < 50:
                try:
                    doc = fitz.open(file_path)
                    if len(doc) > 0 and len(doc) <= 5:
                        print("[!] Scanare degradată cu text minim (<50 caractere). Fallback la Speed 3 (Vision AI)...")
                        pix = doc[0].get_pixmap(dpi=150)
                        tmp_img = f"/tmp/page_0_{os.path.basename(file_path)}.jpg"
                        pix.save(tmp_img)
                        doc.close()
                        vision_res = _process_image_with_vision(tmp_img)
                        if os.path.exists(tmp_img):
                            os.remove(tmp_img)
                        if vision_res and "error" not in vision_res and len(vision_res.get("markdown", "")) > 50:
                            dur_ms = (time.time() - t_ocr_start) * 1000
                            debug_logger.info("ocr_service", "OCR_PROCESS_COMPLETE", data={"file": os.path.basename(file_path), "speed": "Speed3_Fallback", "duration_ms": round(dur_ms, 2)})
                            return vision_res
                except Exception:
                    pass

            dur_ms = (time.time() - t_ocr_start) * 1000
            debug_logger.info("ocr_service", "OCR_PROCESS_COMPLETE", data={"file": os.path.basename(file_path), "speed": "Speed2_Scanned", "duration_ms": round(dur_ms, 2), "chars": len(res.get("markdown", ""))})
            return res

        return {"error": f"Format de fișier nesuportat pentru OCR: {ext}"}

    except Exception as e:
        dur_ms = (time.time() - t_ocr_start) * 1000
        print(f"[!] OCR Error for {file_path}: {e}")
        debug_logger.error("ocr_service", "OCR_PROCESS_FAILED", str(e), details={"file": os.path.basename(file_path), "duration_ms": round(dur_ms, 2)})
        return {"error": str(e)}

# Instanță globală (legacy support)
ocr_service = OCRService()
