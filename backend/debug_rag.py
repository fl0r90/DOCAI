import os
import requests
from core_engine.database import SessionLocal
from core_engine import models
from core_engine.services.chat_service import ChatService

db = SessionLocal()
chat_service = ChatService()

query = "Identifică tranzacția cu cea mai mare valoare din data de 23 februarie 2026 din extrasul de cont. Specifică beneficiarul și soldul final."

# Simulăm extragerea contextului
context = chat_service.get_context_for_query(query, case_id=5)

print("\n--- [ CONTEXT EXTRAS PENTRU GEMMA ] ---")
for i, item in enumerate(context):
    print(f"\n[FRAGMENT {i+1}]:")
    print(item.get('content_text', 'No content'))
    print("-" * 50)
