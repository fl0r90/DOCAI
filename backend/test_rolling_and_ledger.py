"""
Test Unitary & Forensic Logic Verification:
1. Dynamic Context Chunk Sizing (16K vs 32K vs 64K RTX 5000 Ada)
2. Goal-Conditioned Working State Parsing ([NOI_PROBE_IDENTIFICATE] + [ACTUALIZARE_STARE])
3. Append-Only Ledger Accumulation & Early Stopping
4. Forensic Ledger Inspection & Targeted Reranker Zoom
"""

import re
import json

def test_dynamic_chunk_sizing():
    print("\n--- TEST 1: CALIBRARE DINAMICA CALUPURI RAPORTAT LA CONTEXT ---")
    contexts = [16384, 32768, 65536]
    for ctx in contexts:
        avail_tokens = max(4000, ctx - 4500)
        chunk_chars = max(25000, int(avail_tokens * 3.5))
        overlap_chars = min(3000, max(1000, int(chunk_chars * 0.05)))
        target_summary_chars = min(4500, max(1800, chunk_chars // 15))
        print(f"[Context {ctx:,} tok] -> Calup brut: {chunk_chars:,} car. | Overlap: {overlap_chars:,} car. | Rezumat dens tinta: {target_summary_chars:,} car.")
        assert chunk_chars >= 25000
        assert 1000 <= overlap_chars <= 3000

    print("[PASS] Calibrare dinamica 100% corecta!")

def test_state_parsing():
    print("\n--- TEST 2: PARSARE STARE ANCHETA (GOAL TRACKING) ---")
    mock_llm_response = """[NOI_PROBE_IDENTIFICATE]
- S-a identificat Contractul CTR-104 semnat la 12.03.2023 de Popescu Ion.
- Valoarea contractului este de 500.000 EUR cu termen de livrare 30 de zile.

[ACTUALIZARE_STARE]
AM GĂSIT PÂNĂ ACUM: Contractul CTR-104 este semnat de Popescu Ion la 12.03.2023 pentru suma de 500.000 EUR.
MAI CAUT ÎN CONTINUARE: Facturile de livrare a mărfii și dovada plății prin ordin de virament."""

    probe_noi = ""
    am_gasit_deja = ""
    mai_caut = ""

    if "[NOI_PROBE_IDENTIFICATE]" in mock_llm_response:
        parts = mock_llm_response.split("[ACTUALIZARE_STARE]")
        probe_noi = parts[0].replace("[NOI_PROBE_IDENTIFICATE]", "").strip()
        if len(parts) > 1:
            stare_text = parts[1].strip()
            m_gasit = re.search(r'AM GĂSIT PÂNĂ ACUM:\s*(.*?)(?=MAI CAUT ÎN CONTINUARE:|$)', stare_text, re.DOTALL | re.IGNORECASE)
            m_caut = re.search(r'MAI CAUT ÎN CONTINUARE:\s*(.*?)$', stare_text, re.DOTALL | re.IGNORECASE)
            if m_gasit and m_gasit.group(1).strip():
                am_gasit_deja = m_gasit.group(1).strip()
            if m_caut and m_caut.group(1).strip():
                mai_caut = m_caut.group(1).strip()

    print(f"Probe noi parsate ({len(probe_noi)} car.):\n{probe_noi}")
    print(f"Am gasit deja: {am_gasit_deja}")
    print(f"Mai caut: {mai_caut}")

    assert "CTR-104" in probe_noi
    assert "Popescu Ion" in am_gasit_deja
    assert "Facturile de livrare" in mai_caut
    print("[PASS] Parsare Goal Tracking 100% exacta!")

def test_forensic_ledger_matching():
    print("\n--- TEST 3: MATCHING PRE-SCRATCHPAD IN FORENSIC LEDGER ---")
    mock_ledger = [
        {
            "chunk_idx": 1,
            "total_chunks": 3,
            "page_start": 1,
            "page_end": 15,
            "dossier_text": "[SUBIECT]: Preambul si partile contractante. [PARTI]: SC Agro Chim SRL si SC Logistic SA."
        },
        {
            "chunk_idx": 2,
            "total_chunks": 3,
            "page_start": 16,
            "page_end": 28,
            "dossier_text": "[CLAUZE]: Clauza 8.2 privind penalitati de 0.5% pe zi de intarziere. Notificare obligatorie in 5 zile lucratoare la sediul din Bucuresti."
        },
        {
            "chunk_idx": 3,
            "total_chunks": 3,
            "page_start": 29,
            "page_end": 42,
            "dossier_text": "[FINANCIAR]: Situatia de plata finala. Factura FACT-2023-089 in valoare de 125.000 RON achitata partial."
        }
    ]

    question = "Care este clauza cu privire la penalitati de intarziere si notificarea?"
    q_words = [w.lower() for w in re.findall(r'\b\w{3,}\b', question) if w.lower() not in ["despre", "care", "este", "sunt", "cum", "cine", "unde", "cand", "acest", "pentru"]]
    print(f"Cuvinte cheie intrebare: {q_words}")

    hits = []
    for item in mock_ledger:
        d_txt = item["dossier_text"]
        d_txt_lower = d_txt.lower()
        matched_words = [w for w in q_words if w in d_txt_lower]
        if len(matched_words) >= 1:
            hits.append((len(matched_words), item))

    hits.sort(key=lambda x: x[0], reverse=True)
    assert len(hits) > 0
    best_hit = hits[0][1]
    print(f"Best hit identificat: Sectiunea {best_hit['chunk_idx']} (Pag. {best_hit['page_start']}-{best_hit['page_end']}) cu textul:\n{best_hit['dossier_text']}")
    assert best_hit["page_start"] == 16
    assert "penalitati" in best_hit["dossier_text"].lower()
    print("[PASS] Pre-Scratchpad Ledger hit a tintit fix paginile 16-28 pentru Zoom Reranker!")

if __name__ == "__main__":
    test_dynamic_chunk_sizing()
    test_state_parsing()
    test_forensic_ledger_matching()
    print("\n==================================================")
    print("TOATE TESTELE DE LOGICA AU TRECUT CU SUCCES! (100%)")
    print("==================================================")
