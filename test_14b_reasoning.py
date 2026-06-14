import time
import requests
import json

URL = "http://localhost:8000/v1/chat/completions"

def wait_for_vllm():
    print("Waiting for vLLM to start...")
    while True:
        try:
            response = requests.get("http://localhost:8000/v1/models")
            if response.status_code == 200:
                print("vLLM is UP and Ready!")
                break
        except:
            pass
        time.sleep(5)

def run_test(prompt, context_file):
    with open(context_file, 'r') as f:
        context = f.read()
    
    payload = {
        "model": "casperhansen/deepseek-r1-distill-qwen-14b-awq",
        "messages": [
            {"role": "system", "content": "You are a forensic financial analyst. Answer the user based on the provided bank statement text."},
            {"role": "user", "content": f"CONTEXT (Bank Statement):\n{context}\n\nQUESTION:\n{prompt}"}
        ],
        "temperature": 0.1
    }
    
    print(f"Running Test: {prompt[:50]}...")
    start_time = time.time()
    response = requests.post(URL, json=payload)
    end_time = time.time()
    
    if response.status_code == 200:
        result = response.json()
        print("\n--- TEST RESULT ---")
        print(result['choices'][0]['message']['content'])
        print(f"\nTime taken: {end_time - start_time:.2f} seconds")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    wait_for_vllm()
    # Test 1: Pattern Analysis
    run_test("Analizează cheltuielile efectuate între 24 și 27 februarie 2026. Identifică partenerii recurenți și calculează suma totală cheltuită la Carrefour în această perioadă. Există vreo tranzacție care pare a fi o plată de utilități sau factură de servicii recurentă?", "extras_text.txt")
