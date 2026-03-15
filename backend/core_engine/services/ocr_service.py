import os
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
from docling.datamodel.base_models import InputFormat

# Forțăm regimul offline la nivel de proces
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1' 

def chunk_text_with_context(text: str, filename: str, window_size: int = 10, overlap: int = 2) -> list:
    if not text or "Eroare procesare document" in text: return []
    lines = text.split('\n')
    lines = [line for line in lines if line.strip()] 
    
    chunks = []
    step = window_size - overlap
    total_chunks = (len(lines) // step) + (1 if len(lines) % step != 0 else 0)
    
    for i in range(0, len(lines), step):
        chunk_lines = lines[i:i + window_size]
        if not chunk_lines: continue
            
        current_idx = (i // step) + 1
        header = f'> [CONTEXT: Dosar | Document: {filename} | Fragment: {current_idx}/{total_chunks}]\n'
        header += '> ' + '=' * 50 + '\n\n'
        
        chunk_text = header + '\n'.join(chunk_lines)
        chunks.append(chunk_text)
        
    return chunks

def process_document(file_path: str):
    try:
        if not os.path.exists(file_path):
            return {'error': 'Fisier inexistent.', 'markdown': '', 'chunks': []}
            
        filename = os.path.basename(file_path)
        print(f'[*] Docling proceseaza (OCR MODE): {filename}')
        
        # Configuram optiunile pentru OCR complet
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True 
        pipeline_options.do_table_structure = True
        
        # Specificam RapidOCR
        ocr_options = RapidOcrOptions()
        pipeline_options.ocr_options = ocr_options

        # Pentru docling 2.x folosim format_options
        format_options = {
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }

        converter = DocumentConverter(format_options=format_options) 
        result = converter.convert(file_path)
        markdown_content = result.document.export_to_markdown()
        
        # Validare continut minim
        if len(markdown_content.strip()) < 10:
             raise ValueError("Rezultat OCR prea scurt sau invalid.")

        chunks = chunk_text_with_context(markdown_content, filename)
        print(f'[+] OCR Finalizat pentru {filename} ({len(chunks)} chunks)')
        
        return {
            'markdown': markdown_content,
            'chunks': chunks
        }
        
    except Exception as e:
        err_msg = f'Eroare Docling OCR: {str(e)}'
        print(f'[!] {err_msg}')
        return {
            'error': str(e),
            'markdown': err_msg,
            'chunks': []
        }
        
        return {
            'markdown': markdown_content,
            'chunks': chunks
        }
        
    except Exception as e:
        err_msg = f'Eroare Docling OFFLINE: {str(e)}'
        print(f'[!] {err_msg}')
        return {
            'error': str(e),
            'markdown': err_msg,
            'chunks': []
        }
