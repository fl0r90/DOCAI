import sys
sys.path.append('/app')
import re
from sqlalchemy import text
from core_engine.database import SessionLocal
from core_engine.models import Document, DocumentChunk

def extract_intersection_summary():
    with SessionLocal() as db:
        docs = db.query(Document).filter(Document.case_id == 6).all()
        if not docs:
            print("Nu s-au găsit documente.")
            return
            
        instructor_students = {}
        student_occurrences = {}
        
        for doc in docs:
            chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
            instructor = None
            disciplina = None
            
            for c in chunks:
                inst_match = re.search(r"Instructor:\s*([^|\n]+)", c.content)
                disc_match = re.search(r"Disciplina:\s*([^|\n]+)", c.content)
                if inst_match and not instructor:
                    instructor = inst_match.group(1).strip()
                if disc_match and not disciplina:
                    disciplina = disc_match.group(1).strip()
            
            if not instructor:
                for c in chunks:
                    lines = c.content.split('\n')
                    for line in lines:
                        if "Instructor:" in line:
                            instructor = line.split("Instructor:")[-1].split("|")[0].strip()
                            break
            
            if not instructor:
                continue
                
            for c in chunks:
                lines = c.content.split('\n')
                for line in lines:
                    if "|" in line:
                        if any(h in line.lower() for h in ["nume si prenume", "nume și prenume", "email", "status", "---"]):
                            continue
                        parts = [p.strip() for p in line.split("|") if p.strip()]
                        if len(parts) >= 2:
                            name = parts[1] if parts[0].isdigit() else parts[0]
                            status = parts[3] if parts[0].isdigit() and len(parts) >= 4 else (parts[2] if len(parts) >= 3 else "Prezent")
                            
                            name = name.strip()
                            if "prezent" in status.lower():
                                if instructor not in instructor_students:
                                    instructor_students[instructor] = set()
                                instructor_students[instructor].add(name)
                                if name not in student_occurrences:
                                    student_occurrences[name] = []
                                student_occurrences[name].append((instructor, doc.filename))

        all_instructors = list(instructor_students.keys())
        intersected = instructor_students[all_instructors[0]]
        for inst in all_instructors[1:]:
            intersected = intersected.intersection(instructor_students[inst])
            
        print(f"TOTAL_INSTRUCTORS: {len(all_instructors)} ({', '.join(all_instructors)})")
        print(f"TOTAL_COMMON_STUDENTS: {len(intersected)}")
        print("COMMON_STUDENTS_LIST:")
        for name in sorted(list(intersected)):
            files_dict = {}
            for inst, f in student_occurrences[name]:
                if inst not in files_dict:
                    files_dict[inst] = []
                files_dict[inst].append(f)
            
            details = []
            for inst, files in files_dict.items():
                details.append(f"{inst} ({len(files)} cursuri, ex: {', '.join(files[:2])})")
            
            print(f"- {name} -> {'; '.join(details)}")

if __name__ == "__main__":
    extract_intersection_summary()
