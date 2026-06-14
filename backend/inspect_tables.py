from docling.document_converter import DocumentConverter
import os

def inspect():
    pdf_path = "/app/uploads/UCT-Raport-Anual-2011.pdf"
    if not os.path.exists(pdf_path):
        print("Fisier negasit")
        return

    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    
    print(f"[*] Inspectie Tabele pentru {os.path.basename(pdf_path)}")
    for i, table in enumerate(result.document.tables[:10]):
        df = table.export_to_dataframe()
        page = table.prov[0].page_no if table.prov else "unknown"
        print(f"\n--- TABEL {i} (Pagina {page}) ---")
        print(df.to_string(index=False, max_rows=5))

if __name__ == "__main__":
    inspect()
