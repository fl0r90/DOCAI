from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List
import uuid
from ..models import DocumentStorageHelper
from ..services.graph_service import graph_service
from ..services.ocr_service import ocr_service

router = APIRouter(prefix="/cases", tags=["cases"])

@router.get("/")
async def get_cases():
    """Return all cases"""
    return DocumentStorageHelper().get_all_cases()

@router.get("/{case_id}")
async def get_case(case_id: str):
    """Return a specific case by ID"""
    case = DocumentStorageHelper().get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.post("/")
async def create_case(
    title: str = Form(...),
    description: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """Create a new case with associated documents"""
    # Generate unique ID for the case
    case_id = str(uuid.uuid4())
    
    # Create case entry
    case_data = {
        "id": case_id,
        "title": title,
        "description": description,
        "documents": []
    }
    
    # Process each file
    for file in files:
        # Save file to storage
        file_path = f"storage/{case_id}/{file.filename}"
        
        # Read file content
        content = await file.read()
        
        # Perform OCR if it's an image/pdf
        ocr_result = None
        if file.content_type in ["image/jpeg", "image/png", "application/pdf"]:
            ocr_result = ocr_service.process_file(file_path)
        
        # Create document entry
        document_data = {
            "id": str(uuid.uuid4()),
            "name": file.filename,
            "content": content.decode('utf-8') if isinstance(content, bytes) else content,
            "ocr_result": ocr_result,
            "case_id": case_id
        }
        
        # Store document
        DocumentStorageHelper().save_document(document_data)
        
        # Add to case
        case_data["documents"].append(document_data)
    
    # Save case
    DocumentStorageHelper().save_case(case_data)
    
    # Process documents for graph relationships
    graph_service.process_case_documents(case_data)
    
    return {"message": "Case created successfully", "case_id": case_id}

@router.put("/{case_id}")
async def update_case(case_id: str, title: str = Form(...), description: str = Form(...)):
    """Update an existing case"""
    case = DocumentStorageHelper().get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Update case data
    updated_case = {
        **case,
        "title": title,
        "description": description
    }
    
    # Save updated case
    DocumentStorageHelper().save_case(updated_case)
    
    return {"message": "Case updated successfully"}

@router.delete("/{case_id}")
async def delete_case(case_id: str):
    """Delete a case and all associated documents"""
    case = DocumentStorageHelper().get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Delete all associated documents
    for document in case.get("documents", []):
        DocumentStorageHelper().delete_document(document["id"])
    
    # Delete the case itself
    DocumentStorageHelper().delete_case(case_id)
    
    return {"message": "Case deleted successfully"}
