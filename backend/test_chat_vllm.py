import sys
import os

# Adaugam backend in path
sys.path.append("/app")

from core_engine.services.chat_service import query_investigator

def test_vllm():
    print("[*] Initiating Test with DeepSeek-R1-14B (vLLM) on Case ID 5...")
    question = "Analizează cheltuielile efectuate între 24 și 27 februarie 2026. Identifică partenerii recurenți și calculează suma totală cheltuită la Carrefour în această perioadă. Există vreo tranzacție care pare a fi o plată de utilități sau factură de servicii recurentă?"
    print(f"[*] Question: {question}")
    
    result = query_investigator(5, question)
    
    print("\n" + "="*50)
    print("FINAL ANSWER:")
    print("="*50)
    print(result.get("answer", "No answer generated."))
    
    print("\n" + "="*50)
    print("CITATIONS:")
    print("="*50)
    for c in result.get("citations", []):
        print(f"- Doc: {c['filename']} (Page: {c['page']}) -> {c['text'][:100]}...")

if __name__ == "__main__":
    test_vllm()
