import os
import json
from typing import Dict, List, Any

class DocumentStorage:
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
