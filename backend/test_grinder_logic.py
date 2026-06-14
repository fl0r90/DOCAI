
import asyncio
import json
import unittest
from unittest.mock import MagicMock, AsyncMock
import sys
import os

# Adăugăm calea către backend pentru a putea importa serviciile
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mocking environment variables before imports
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["OLLAMA_URL"] = "http://localhost:11434"
os.environ["FORENSIC_DATABASE_URL"] = "sqlite:///./test_forensic.db"

from core_engine.services.grinder import parse_markdown_table, extract_forensic_data
from core_engine.services.llm_service import LLMService

class TestGrinderRefactor(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        # Mock pentru LLMService
        self.mock_llm = MagicMock(spec=LLMService)
        self.mock_llm.generate = AsyncMock()
        self.mock_llm.close = AsyncMock()
        
        # Mock pentru Redis
        import redis
        self.patcher_redis = unittest.mock.patch('redis.from_url')
        self.mock_redis = self.patcher_redis.start()
        self.mock_redis_client = MagicMock()
        self.mock_redis.return_value = self.mock_redis_client
        
        # Mock pentru DB _save_transaction_live pentru a nu scrie în DB reală în timpul testului logic
        self.patcher_save = unittest.mock.patch('core_engine.services.grinder._save_transaction_live')
        self.mock_save = self.patcher_save.start()

    def tearDown(self):
        self.patcher_redis.stop()
        self.patcher_save.stop()

    def test_parse_markdown_table(self):
        md = """
| Data | Descriere | Debit | Credit | Sold |
|------|-----------|-------|--------|------|
| 01.03.2026 | PLATA FACTURA | 150.00 | | 850.00 |
| 02.03.2026 | INCASARE | | 1000.00 | 1850.00 |
"""
        rows = parse_markdown_table(md)
        self.assertEqual(len(rows), 3) # Header + 2 rows
        self.assertEqual(rows[0], ["Data", "Descriere", "Debit", "Credit", "Sold"])
        self.assertEqual(rows[1][0], "01.03.2026")
        self.assertEqual(rows[1][2], "150.00")

    async def test_extract_forensic_data_flow(self):
        # Simulăm un tabel Markdown complex
        md_content = """
| Data Operarii | Detalii Tranzactie | Suma (-) | Suma (+) | Balanta |
|---------------|--------------------|----------|----------|---------|
| 10.04.2026    | TRANSFER CATRE X   | 500,00   |          | 1500,00 |
| 11.04.2026    | DEPOZIT NUMERAR    |          | 200,00   | 1700,00 |
"""
        layout_data = {
            "items": [
                {"type": "TABLE", "content": md_content}
            ]
        }
        
        # Simulăm răspunsul LLM pentru mapping-ul coloanelor
        self.mock_llm.generate.return_value = {
            "date_idx": 0,
            "desc_idx": 1,
            "amount_idx": 2,
            "credit_idx": 3,
            "balance_idx": 4
        }
        
        # Patch LLMService în interiorul extract_forensic_data
        with unittest.mock.patch('core_engine.services.grinder.LLMService', return_value=self.mock_llm):
            result = await extract_forensic_data(layout_data, filename="test.pdf", doc_id=1)
            
            # Verificăm dacă datele au fost extrase
            fin_data = result["metadata"]["financial_data"]
            self.assertEqual(len(fin_data), 2)
            
            # Verificăm prima tranzacție (Debit -> Negativ)
            self.assertEqual(fin_data[0]["suma"], -500.0)
            self.assertEqual(fin_data[0]["data"], "10.04.2026")
            
            # Verificăm a doua tranzacție (Credit -> Pozitiv)
            self.assertEqual(fin_data[1]["suma"], 200.0)
            
            # Verificăm dacă s-a apelat salvarea în DB de 2 ori
            self.assertEqual(self.mock_save.call_count, 2)

if __name__ == "__main__":
    asyncio.run(unittest.main())
