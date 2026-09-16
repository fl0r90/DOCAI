"""
Script pentru rularea exclusivă a auditului AI Forensic fără a relua OCR-ul sau indexarea vectorială.
Utilizare:
    docker exec v2-backend python run_ai_audit_only.py [DOC_ID]
"""

import sys
import asyncio
from core_engine.services.deep_audit_service import DeepForensicAuditor

async def main():
    target_id = int(sys.argv[1]) if len(sys.argv) > 1 else 145
    print(f"[*] Lansare Deep Forensic AI Audit pentru document ID: {target_id}...")
    auditor = DeepForensicAuditor(target_id)
    res = await auditor.run_audit()
    print(f"[+] Finalizat cu succes: {res}")

if __name__ == "__main__":
    asyncio.run(main())
