from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from ..models import DocumentStorage
import uuid

def upsert_document_chunk(db: Session, chunk_data: dict, vector: list):
    """
    Upserts a Docling-parsed document chunk into PostgreSQL with pgvector and JSONB.
    
    Expected chunk_data format:
    {
        "id": str (optional UUID),
        "parent_doc_id": str (UUID),
        "content": str (raw text),
        "metadata": dict,
        "extra": dict (optional)
    }
    """
    
    # Use provided ID or generate one (Note: for true idempotency, ID should be stable)
    chunk_id = chunk_data.get('id')
    if not chunk_id:
        chunk_id = str(uuid.uuid4())
        
    parent_id = chunk_data.get('parent_doc_id')
    content = chunk_data.get('content', '')
    
    # Map Docling "metadata" or "extra" fields directly into raw_metadata
    raw_meta = chunk_data.get('metadata', {})
    if 'extra' in chunk_data:
        raw_meta['extra'] = chunk_data['extra']
        
    # Build the insert statement with ON CONFLICT DO UPDATE
    stmt = insert(DocumentStorage).values(
        id=chunk_id,
        parent_doc_id=parent_id,
        content_text=content,
        embedding=vector,
        raw_metadata=raw_meta
    )
    
    # Ensure idempotency
    stmt = stmt.on_conflict_do_update(
        index_elements=['id'],
        set_={
            'content_text': stmt.excluded.content_text,
            'embedding': stmt.excluded.embedding,
            'raw_metadata': stmt.excluded.raw_metadata
        }
    )
    
    db.execute(stmt)
    db.commit()
    return chunk_id
