import os
import json
from typing import Dict, List, Any
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Float, DECIMAL, JSON
from sqlalchemy.orm import relationship
from .database import Base
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="investigator")
    is_active = Column(Boolean, default=True)
    needs_password_change = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Case(Base):
    __tablename__ = "cases"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(Text)
    master_id = Column(Integer)
    status = Column(String, default="open")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    user_id = Column(Integer, ForeignKey("users.id")) # renamed from uploaded_by to match migration guide
    filename = Column(String)
    file_hash = Column(String)
    file_path = Column(String)
    doc_category = Column(String)
    doc_type = Column(String)
    doc_date = Column(String)
    doc_number = Column(String)
    total_amount = Column(Float)
    ai_summary = Column(Text)
    risk_score = Column(Float, default=0.0)
    risk_analysis = Column(Text)
    doc_metadata = Column(JSON) # from migration guide
    processed = Column(Boolean, default=False)
    status = Column(String, default="QUEUED")
    raw_text = Column(Text)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    chunk_index = Column(Integer)
    content = Column(Text)
    page_number = Column(Integer)
    spatial = Column(Text)
    parent_chunk_id = Column(Integer, ForeignKey("document_chunks.id"))
    embedding = Column(Vector(1024)) # Updated to 1024 for BGE-M3

class DocumentStorage(Base): # The table used by storage_service.py
    __tablename__ = "document_storage"
    id = Column(UUID(as_uuid=True), primary_key=True)
    parent_doc_id = Column(UUID(as_uuid=True))
    content_text = Column(Text, nullable=False)
    embedding = Column(Vector(1024))
    raw_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MasterEntity(Base):
    __tablename__ = "master_entities"
    id = Column(Integer, primary_key=True, index=True)
    official_name = Column(String, index=True)
    cui_cif_cnp = Column(String, index=True)
    entity_type = Column(String)
    address = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DocumentEntityLink(Base):
    __tablename__ = "document_entity_links"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    entity_id = Column(Integer, ForeignKey("master_entities.id"))
    role = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FinancialItem(Base):
    __tablename__ = "financial_items"
    id = Column(String, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    doc_number = Column(String)
    doc_filename = Column(String)
    transaction_date = Column(String)
    description = Column(Text)
    amount = Column(Float)
    currency = Column(String, default="RON")
    doc_type = Column(String)
    transaction_type = Column(String)
    cui_source = Column(String)
    iban_source = Column(String)
    cui_destination = Column(String)
    iban_destination = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CaseMember(Base):
    __tablename__ = "case_members"
    case_id = Column(Integer, ForeignKey("cases.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    added_by = Column(Integer, ForeignKey("users.id"))
    added_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action_type = Column(String)
    details = Column(Text)
    severity = Column(String, default="INFO")
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SystemSetting(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    role = Column(String) # "user" sau "assistant"
    content = Column(Text)
    sql = Column(Text)  # Jurnal de investigație (trace logs) serializat ca JSON array
    citations = Column(JSON)  # Citatele [REF x] asociate răspunsului
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DocumentStorageHelper: # Renamed from DocumentStorage
    def __init__(self):
        self.storage_path = "storage"
        os.makedirs(self.storage_path, exist_ok=True)
        
    def get_all_cases(self) -> List[Dict[str, Any]]:
        """Return all cases from storage"""
        try:
            with open(f"{self.storage_path}/cases.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def get_case(self, case_id: str) -> Dict[str, Any]:
        """Return a specific case by ID"""
        cases = self.get_all_cases()
        for case in cases:
            if case["id"] == case_id:
                return case
        return None
    
    def save_case(self, case_data: Dict[str, Any]) -> None:
        """Save a case to storage"""
        cases = self.get_all_cases()
        # Remove existing case with same ID
        cases = [c for c in cases if c["id"] != case_data["id"]]
        cases.append(case_data)
        
        with open(f"{self.storage_path}/cases.json", "w") as f:
            json.dump(cases, f, indent=2)
    
    def delete_case(self, case_id: str) -> None:
        """Delete a case from storage"""
        cases = self.get_all_cases()
        updated_cases = [c for c in cases if c["id"] != case_id]
        
        with open(f"{self.storage_path}/cases.json", "w") as f:
            json.dump(updated_cases, f, indent=2)
    
    def get_case_documents(self, case_id: str) -> List[Dict[str, Any]]:
        """Return all documents for a specific case"""
        case = self.get_case(case_id)
        if not case:
            return []
        return case.get("documents", [])
    
    def save_document(self, document_data: Dict[str, Any]) -> None:
        """Save a document to storage"""
        # Save document content
        doc_path = f"{self.storage_path}/{document_data['case_id']}"
        os.makedirs(doc_path, exist_ok=True)
        
        with open(f"{doc_path}/{document_data['id']}.json", "w") as f:
            json.dump(document_data, f, indent=2)
    
    def delete_document(self, document_id: str) -> None:
        """Delete a document from storage"""
        # This is a simplified implementation - in reality you'd want to find
        # the case that contains this document and remove it from there too
        pass
