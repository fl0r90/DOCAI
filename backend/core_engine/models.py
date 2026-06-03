from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Date, Table, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from sqlalchemy.ext.declarative import declarative_base

# Două baze diferite
AuthBase = declarative_base()
ForensicBase = declarative_base()

# --- MODELE AUTH_DB ---
class User(AuthBase):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="WORKER") # MASTER, ADMIN, WORKER
    is_active = Column(Integer, default=1)
    needs_password_change = Column(Integer, default=1)
    reset_requested = Column(Integer, default=0)
    priority = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- MODELE FORENSIC_DB ---
case_worker_link = Table(
    'case_worker_link',
    ForensicBase.metadata,
    Column('user_id', Integer),
    Column('case_id', Integer, ForeignKey('cases.id'))
)

class Case(ForensicBase):
    __tablename__ = "cases"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    master_id = Column(Integer, index=True) # Coloana de izolare
    status = Column(String, default="OPEN") 
    case_summary = Column(Text, nullable=True)
    summary_doc_hash = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    documents = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="case", cascade="all, delete-orphan")
    chat_history = relationship("ChatMessage", back_populates="case", cascade="all, delete-orphan")

class Document(ForensicBase):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_hash = Column(String, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    user_id = Column(Integer)
    status = Column(String, default="QUEUED")
    doc_type = Column(String, nullable=True) # FACTURA, CONTRACT, BALANTA, OP, ALTUL
    doc_metadata = Column(JSON, nullable=True) # Stocăm datele parțiale aici
    processing_progress = Column(Integer, default=0) # Ultimul segment procesat
    issue_date = Column(String, nullable=True)
 # Data oficială (din document)
    ai_summary = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    case = relationship("Case", back_populates="documents")
    financial_items = relationship("FinancialItem", back_populates="source_document", cascade="all, delete-orphan")
    entity_links = relationship("DocumentEntityLink", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class ChatMessage(ForensicBase):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    role = Column(String) 
    content = Column(Text)
    sql = Column(Text, nullable=True)
    citations = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    case = relationship("Case", back_populates="chat_history")

class MasterEntity(ForensicBase):
    __tablename__ = "master_entities"
    id = Column(Integer, primary_key=True, index=True)
    official_name = Column(String, index=True)
    cui_cif_cnp = Column(String, nullable=True, index=True) 
    address = Column(Text, nullable=True)
    entity_type = Column(String, default="FIRMA")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    document_links = relationship("DocumentEntityLink", back_populates="entity")

class DocumentEntityLink(ForensicBase):
    __tablename__ = "document_entity_links"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    entity_id = Column(Integer, ForeignKey("master_entities.id"))
    role = Column(String, nullable=True)
    document = relationship("Document", back_populates="entity_links")
    entity = relationship("MasterEntity", back_populates="document_links")

class DocumentStorage(ForensicBase):
    __tablename__ = "document_storage"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_doc_id = Column(UUID(as_uuid=True), index=True, nullable=True)
    content_text = Column(Text, nullable=False)
    embedding = Column(Vector(1024))
    raw_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # GIN Index for fast JSONB querying and Full Text Search
    __table_args__ = (
        Index('ix_doc_storage_metadata_gin', 'raw_metadata', postgresql_using='gin'),
        Index('ix_doc_storage_content_gin', func.to_tsvector('romanian', 'content_text'), postgresql_using='gin'),
    )

class DocumentChunk(ForensicBase):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    parent_chunk_id = Column(Integer, ForeignKey("document_chunks.id"), nullable=True)
    content = Column(Text)
    page_number = Column(Integer, nullable=True)
    spatial = Column(String, nullable=True)
    embedding = Column(Vector(1024))
    document = relationship("Document", back_populates="chunks")
class FinancialItem(ForensicBase):
    __tablename__ = "financial_items"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4())) # UUID
    document_id = Column(Integer, ForeignKey("documents.id"))
    doc_number = Column(String, nullable=True) 
    doc_filename = Column(String, nullable=True) 
    transaction_date = Column(String, nullable=True)
    description = Column(String)
    amount = Column(Float) 
    currency = Column(String, default="RON")
    
    # Forensic Fields
    doc_type = Column(String, nullable=True) # EXTRAS, FACTURA
    transaction_type = Column(String, nullable=True) # PLATA, INCASARE, FACTURARE
    cui_source = Column(String, index=True, nullable=True)
    iban_source = Column(String, index=True, nullable=True)
    cui_destination = Column(String, index=True, nullable=True)
    iban_destination = Column(String, index=True, nullable=True)
    
    source_document = relationship("Document", back_populates="financial_items")

class AuditLog(ForensicBase):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    action_type = Column(String)
    details = Column(Text, nullable=True)
    severity = Column(String, default="INFO")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    case = relationship("Case", back_populates="audit_logs")

class SystemSetting(ForensicBase):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True) 
    value = Column(String)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

Base = ForensicBase
