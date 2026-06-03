import os
import gc
import torch
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
from docling.datamodel.base_models import InputFormat

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
# DEZACTIVĂM GPU pentru Docling (Stabilitate maximă pe CPU)
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

def unload_vram():
    """Eliberează forțat memoria GPU ocupată de PyTorch/Docling."""
    # Deși rulăm pe CPU, păstrăm funcția pentru curățenie generală
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def process_document(file_path: str):
    """Extrage layout-ul structurat folosind CPU pentru stabilitate."""
    import time
    for attempt in range(2):
        try:
            if not os.path.exists(file_path):
                return {"error": "Fisier inexistent"}

            # Configurare pentru stabilitate maximă
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = True
            pipeline_options.do_table_structure = True
            
            # Forțăm folosirea CPU în pipeline_options dacă e suportat, 
            # altfel setarea de mediu de mai sus e suficientă.
            
            converter = DocumentConverter(format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            })
            
            print(f"[*] Docling: Pornire analiză structurală pe CPU ({os.path.basename(file_path)}) - Tentativa {attempt+1}")
            result = converter.convert(file_path)
            doc = result.document
            
            layout_items = []
            chunks = []
            
            # --- AGNOSTIC HEADER EXTRACTION ---
            # Luăm primele 500-1000 de caractere ca și context global (antet)
            # Acesta va fi injectat în fiecare chunk pentru a păstra contextul
            full_markdown = doc.export_to_markdown()
            header_context = ""
            lines = full_markdown.split('\n')
            header_lines = []
            for line in lines[:15]: # Primele 15 linii sunt de obicei antetul
                if '|' not in line and line.strip(): # Evităm tabelele în antet
                    header_lines.append(line.strip())
            header_context = " | ".join(header_lines[:5]) # Păstrăm esența (primele 5 rânduri de text)

            # 1. Procesare Texte
            for item in doc.texts:
                page_no = 1
                spatial = ""
                if item.prov:
                    p = item.prov[0]
                    page_no = p.page_no
                    if p.bbox:
                        b = p.bbox
                        spatial = f"x={b.l},y={b.t},w={b.r-b.l},h={b.b-b.t}"
                
                content = item.text
                if content and len(content.strip()) > 5:
                    # Injectăm contextul global în mod agnostic
                    enriched_content = f"[{header_context}] {content}" if header_context else content
                    layout_items.append({"type": "TEXT", "content": content, "page_no": page_no, "spatial": spatial})
                    chunks.append({"text": enriched_content, "page": page_no, "spatial": spatial})

            # 2. Procesare Tabele
            for item in doc.tables:
                page_no = 1
                spatial = ""
                if item.prov:
                    p = item.prov[0]
                    page_no = p.page_no
                    if p.bbox:
                        b = p.bbox
                        spatial = f"x={b.l},y={b.t},w={b.r-b.l},h={b.b-b.t}"
                
                try:
                    full_md = item.export_to_markdown()
                    # Pentru tabele, injectăm header-ul în fiecare bucată de tabel
                    enriched_md = f"Context: {header_context}\n\n{full_md}" if header_context else full_md
                    layout_items.append({"type": "TABLE", "content": full_md, "page_no": page_no, "spatial": spatial})
                    chunks.append({"text": enriched_md, "page": page_no, "spatial": spatial})
                except: pass


            return {
                "items": layout_items,
                "chunks": chunks,
                "filename": os.path.basename(file_path),
                "markdown": doc.export_to_markdown(),
                "outline": [] 
            }
        except Exception as e:
            print(f"[!] Eroare Docling GPU (Tentativa {attempt+1}): {e}")
            if "out of memory" in str(e).lower():
                unload_vram()
                time.sleep(5)
                continue
            return {"error": str(e)}
        finally:
            unload_vram()
    return {"error": "Esec repetat OOM GPU"}
