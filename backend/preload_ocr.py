import os
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions

# Setari environment pentru OFFLINE
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['RAPIDOCR_CACHE'] = '/app/ocr_cache/rapidocr'

def test_ocr():
    test_pdf = "/app/uploads/Nota de plată.pdf"
    if not os.path.exists(test_pdf):
        print(f"[-] Fisierul de test nu exista la {test_pdf}")
        return

    print(f"[*] Testare OCR OFFLINE pentru: {test_pdf}")
    
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    
    ocr_options = RapidOcrOptions()
    pipeline_options.ocr_options = ocr_options

    try:
        converter = DocumentConverter(pipeline_options=pipeline_options)
        result = converter.convert(test_pdf)
        text = result.document.export_to_markdown()
        print(f"[+] Succes! Text extras (primele 200 caractere):\n{text[:200]}")
    except Exception as e:
        print(f"[!] EROARE TEST OCR: {e}")

if __name__ == "__main__":
    test_ocr()
