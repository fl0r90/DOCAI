import os
from PIL import Image
import pytesseract
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions

class OCRService:
    def __init__(self):
        # Configurare pipeline Docling
        self.pipeline_options = PdfPipelineOptions()
        self.pipeline_options.do_ocr = True
        
        # RapidOCR este motorul preferat în acest setup (vezi preload_ocr.py)
        ocr_options = RapidOcrOptions()
        self.pipeline_options.ocr_options = ocr_options
        
        # Singleton converter pentru eficiență
        self.converter = None

    def _get_converter(self):
        if self.converter is None:
            self.converter = DocumentConverter(pipeline_options=self.pipeline_options)
        return self.converter

    def process_file(self, file_path: str) -> dict:
        """Metodă veche/simplă pentru compatibilitate."""
        try:
            if file_path.endswith(('.jpg', '.jpeg', '.png')):
                with Image.open(file_path) as img:
                    extracted_text = pytesseract.image_to_string(img)
                    return {"text": extracted_text, "format": "plain_text"}
            return {"error": "Folosiți process_document pentru PDF/OCR complex."}
        except Exception as e:
            return {"error": str(e)}

def process_document(file_path: str):
    """
    Pipeline principal OCR folosit de Worker (tasks.py).
    Returnează Markdown și Chunks structurați.
    """
    try:
        service = OCRService()
        converter = service._get_converter()
        result = converter.convert(file_path)
        
        md_text = result.document.export_to_markdown()
        
        # Extracție chunks cu metadate spațiale (cerute de tasks.py)
        chunks = []
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
            
        return {
            "markdown": md_text,
            "chunks": chunks
        }
    except Exception as e:
        print(f"[!] OCR Error for {file_path}: {e}")
        return {"error": str(e)}

# Instanță globală (legacy support)
ocr_service = OCRService()
