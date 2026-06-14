from docling.document_converter import DocumentConverter
from pathlib import Path
import os

source = Path('/app/uploads/SNP_20250204073643_OMV-Petrom-Noutati-Investitori-T4-2024.pdf')
converter = DocumentConverter()
result = converter.convert(source)
doc = result.document

print(f'Document has {len(doc.texts)} text items')
for i, item in enumerate(doc.texts[:10]):
    prov = getattr(item, 'prov', None)
    print(f'Item {i}: text="{item.text[:20]}" prov={prov}')
    if prov:
        p = prov[0]
        # BoundingBox(l=..., t=..., r=..., b=...)
        bbox = getattr(p, 'bbox', None)
        page_no = getattr(p, 'page_no', 'N/A')
        print(f'  Page: {page_no} BBox: {bbox}')
        if bbox:
            print(f'    l={bbox.l}, t={bbox.t}, r={bbox.r}, b={bbox.b}')
