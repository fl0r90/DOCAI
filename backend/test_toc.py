"""
Test unitar pentru modulul TOC (Table of Contents / Deep Forensic Document Outline).
Validează extragerea ierarhică pe un contract sintetic de cereale de 3 pagini:
Agroterra Logistics SRL vs BioFruct Distribution SRL.
"""

import unittest
from core_engine.services.toc.patterns import classify_and_normalize_heading
from core_engine.services.toc.schemas import DocumentTOC, TOCItem
from core_engine.services.toc.extractor import TOCExtractor
from core_engine.services.toc.service import TOCService


SYNTHETIC_GRAIN_CONTRACT = """<!-- PAGE: 1 -->
CONTRACT DE VÂNZARE-CUMPĂRARE CEREALE NR. 104/2026

CAPITOLUL I: PĂRȚILE CONTRACTANTE
Prezentul contract s-a încheiat între SC Agroterra Logistics SRL, în calitate de Vânzător, și SC BioFruct Distribution SRL, în calitate de Cumpărător.

Articolul 1: Identificarea Părților
Vânzătorul cu sediul în Timișoara, CUI RO361536, și Cumpărătorul cu sediul în Arad, CUI RO892145.

CAPITOLUL II: OBIECTUL CONTRACTULUI
Vânzătorul se obligă să livreze, iar Cumpărătorul să recepționeze și să plătească cantitatea de grâu panificație convenită.

Articolul 2: Cantitatea și Calitatea Grâului
Cantitatea contractată este de 1.000 tone grâu STAS 2026, umiditate max 14%, impurități max 2%.

<!-- PAGE: 2 -->
CAPITOLUL III: PREȚUL ȘI MODALITATEA DE PLATĂ
Prețul total al mărfii și condițiile de decontare prin virament bancar.

Articolul 3: Prețul per Tonă
Prețul este de 1.100 RON / tonă fără TVA, livrare franco depozit Vânzător.

CAPITOLUL IV: PENALITĂȚI ȘI RĂSPUNDERE CONTRACTUALĂ
Pentru neîndeplinirea culpabilă a obligațiilor de livrare sau plată se percep penalități zilnice.

Articolul 4: Întârzieri la Livrare
Depășirea termenului de livrare atrage răspunderea exclusivă a Vânzătorului.

Articolul 4.1: Cuantumul Penalităților
Pentru fiecare zi de întârziere, partea în culpă datorează penalități de 0.5% pe zi calculate din valoarea mărfii nelivrate.

<!-- PAGE: 3 -->
ANEXA 1: BORDEROU RECEPȚIE ȘI TICHETE DE CÂNTAR
Evidența cantităților descărcate la siloz conform cântăririlor oficiale.

Proces-Verbal nr. PV-882/2026 de Recepție Calitativă
Comisia a constatat un deficit de 61.50 tone față de avizul de expediție inițial.

Tichet Cântar nr. TC-1094 din data de 14.02.2026
Greutate brută: 42.10 tone, Tara: 16.20 tone, Greutate netă: 25.90 tone grâu recepționat.
"""


class TestTOCModule(unittest.TestCase):

    def test_classify_and_normalize_heading(self):
        # Capitole
        res = classify_and_normalize_heading("CAPITOLUL I: PĂRȚILE CONTRACTANTE")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], "chapter")
        self.assertEqual(res[1], 1)
        self.assertEqual(res[2], "Capitolul I: PĂRȚILE CONTRACTANTE")

        # Articole simple și compuse
        res = classify_and_normalize_heading("Articolul 4: Întârzieri")
        self.assertIsNotNone(res)
        self.assertEqual(res[0], "article")
        self.assertEqual(res[1], 2)

        res_sub = classify_and_normalize_heading("Articolul 4.1: Cuantumul Penalităților")
        self.assertIsNotNone(res_sub)
        self.assertEqual(res_sub[0], "article")
        self.assertEqual(res_sub[1], 3)

        # Anexe
        res_anx = classify_and_normalize_heading("ANEXA 1: BORDEROU RECEPȚIE")
        self.assertIsNotNone(res_anx)
        self.assertEqual(res_anx[0], "annex")
        self.assertEqual(res_anx[1], 1)

        # Acte administrative / Procese verbale / Tichete
        res_pv = classify_and_normalize_heading("Proces-Verbal nr. PV-882/2026")
        self.assertIsNotNone(res_pv)
        self.assertEqual(res_pv[0], "minute")

        res_tc = classify_and_normalize_heading("Tichet Cântar nr. TC-1094")
        self.assertIsNotNone(res_tc)
        self.assertEqual(res_tc[0], "minute")

    def test_extractor_candidates(self):
        extractor = TOCExtractor(
            raw_text=SYNTHETIC_GRAIN_CONTRACT,
            document_id=42,
            document_title="Contract Vanzare Cereale Agroterra"
        )
        candidates = extractor.extract_candidates()
        
        # Verificăm că a extras toate antetele cheie (4 capitole, 5 articole, 1 anexă, 2 acte)
        self.assertGreaterEqual(len(candidates), 10)

        # Verificăm maparea corectă a paginilor
        pages_found = {c["title"]: c["page_start"] for c in candidates}
        
        # Pagina 1
        self.assertEqual(pages_found.get("CAPITOLUL I: PĂRȚILE CONTRACTANTE"), 1)
        self.assertEqual(pages_found.get("Articolul 1: Identificarea Părților"), 1)
        self.assertEqual(pages_found.get("CAPITOLUL II: OBIECTUL CONTRACTULUI"), 1)

        # Pagina 2
        self.assertEqual(pages_found.get("CAPITOLUL III: PREȚUL ȘI MODALITATEA DE PLATĂ"), 2)
        self.assertEqual(pages_found.get("Articolul 4.1: Cuantumul Penalităților"), 2)

        # Pagina 3
        self.assertEqual(pages_found.get("ANEXA 1: BORDEROU RECEPȚIE ȘI TICHETE DE CÂNTAR"), 3)
        self.assertIn("Proces-Verbal nr. PV-882/2026 de Recepție Calitativă", pages_found)
        self.assertEqual(pages_found["Proces-Verbal nr. PV-882/2026 de Recepție Calitativă"], 3)

    def test_heuristic_tree_hierarchy(self):
        extractor = TOCExtractor(
            raw_text=SYNTHETIC_GRAIN_CONTRACT,
            document_id=42,
            document_title="Contract Vanzare Cereale Agroterra"
        )
        candidates = extractor.extract_candidates()
        toc = extractor.build_heuristic_tree(candidates, total_pages=3)

        self.assertIsInstance(toc, DocumentTOC)
        self.assertEqual(toc.total_pages, 3)
        self.assertGreaterEqual(len(toc.items), 4)

        # Verificăm că Capitolul IV (level 1) conține Articolul 4 (level 2) ca și copil
        cap_4 = next((item for item in toc.items if "CAPITOLUL IV" in item.title), None)
        self.assertIsNotNone(cap_4)
        self.assertGreaterEqual(len(cap_4.children), 1)

        # Verificăm randarea ca text lizibil
        readable = toc.to_readable_text()
        self.assertIn("=== CUPRINS STRUCTURAL", readable)
        self.assertIn("[Pag. 1]", readable)
        self.assertIn("[Pag. 2]", readable)
        self.assertIn("[Pag. 3]", readable)

        # Verificăm lista liniară flat
        flat = toc.to_flat_list()
        self.assertGreaterEqual(len(flat), 10)
        self.assertTrue(any(f["page_start"] == 2 and "4.1" in f["title"] for f in flat))

    def test_service_generation_fallback(self):
        service = TOCService()
        # Testăm generarea fără LLM (heuristic mode garantat)
        toc = service.generate_toc(
            raw_text=SYNTHETIC_GRAIN_CONTRACT,
            total_pages=3,
            document_id=42,
            document_title="Contract Agroterra",
            use_llm=False
        )
        self.assertIsInstance(toc, DocumentTOC)
        self.assertEqual(toc.total_pages, 3)
        self.assertGreaterEqual(len(toc.items), 4)


if __name__ == "__main__":
    unittest.main()
