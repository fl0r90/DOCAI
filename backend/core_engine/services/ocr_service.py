import os
from docling.document_converter import DocumentConverter

def process_document(file_path: str):
    """
    Procesează documente forțând utilizarea CPU pentru OCR pentru a evita conflictele de VRAM.
    """
    # Salvăm starea originală a CUDA_VISIBLE_DEVICES
    old_cuda = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    try:
        if not os.path.exists(file_path):
            return "Eroare: Fișier inexistent."
            
        print(f"[*] Docling procesează (CPU FORCED): {file_path}")
        
        # Ascundem GPU de PyTorch/Docling/OCR
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
        
        # Inițializăm converter-ul (va rula pe CPU din cauza variabilei de mediu)
        converter = DocumentConverter() 
        result = converter.convert(file_path)
        
        markdown_content = result.document.export_to_markdown()
        print(f"[+] OCR finalizat pe CPU pentru {os.path.basename(file_path)}")
        return markdown_content
        
    except Exception as e:
        print(f"[-] Eroare Docling: {e}")
        return f"Eroare procesare document: {str(e)}"
    finally:
        # Restaurăm starea GPU pentru alte procese (dacă e cazul)
        if old_cuda:
            os.environ["CUDA_VISIBLE_DEVICES"] = old_cuda
        else:
            os.environ.pop("CUDA_VISIBLE_DEVICES", None)
