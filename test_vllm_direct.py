import requests
import json
import time

VLLM_URL = "http://localhost:8001/v1/chat/completions"

def test_direct_vllm():
    print("[*] Test direct vLLM cu TurboQuant (DeepSeek-R1)...")
    
    payload = {
        "model": "casperhansen/deepseek-r1-distill-qwen-14b-awq",
        "messages": [
            {"role": "user", "content": "Salut! Cine ești și ce motor de accelerare KV Cache folosești acum? Răspunde scurt în română."}
        ],
        "temperature": 0.1,
        "max_tokens": 512
    }
    
    start_time = time.time()
    try:
        response = requests.post(VLLM_URL, json=payload, timeout=300)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"\n[+] Răspuns primit în {elapsed:.2f} secunde:")
            print("-" * 50)
            print(content)
            print("-" * 50)
        else:
            print(f"[!] Eroare API (Status {response.status_code}): {response.text}")
    except Exception as e:
        print(f"[!] Eroare conexiune: {e}")

if __name__ == "__main__":
    test_direct_vllm()
