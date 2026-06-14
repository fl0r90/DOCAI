import ollama
import subprocess
import os
import json

def run_cmd(cmd):
    print(f"-> Executing: {cmd}")
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout

def main():
    client = ollama.Client(host='http://localhost:11434')
    prompt = """Creeaza o aplicatie Flask intr-un singur fisier numit 'chess_final.py'. 
    Trebuie sa contina:
    - Logica backend cu python-chess.
    - Frontend cu chessboard.js si jquery de pe CDN.
    - AI simplu (random sau greedy) pentru negru.
    - Serverul sa ruleze pe 0.0.0.0:5005.
    Pune codul intre tag-uri CODE_START si CODE_END."""
    
    print("[*] Cerem codul de la Qwen...")
    resp = client.generate(model='qwen2.5-coder:7b', prompt=prompt)
    response_text = resp['response']
    
    if "CODE_START" in response_text:
        code = response_text.split("CODE_START")[1].split("CODE_END")[0].strip()
    else:
        # Fallback to markdown
        if "```python" in response_text:
            code = response_text.split("```python")[1].split("```")[0].strip()
        else:
            code = response_text
            
    with open("chess_final.py", "w") as f:
        f.write(code)
    
    print("[*] Instalam python-chess...")
    run_cmd("./venv/bin/pip install python-chess flask")
    
    print("[*] Pornim serverul pe 5005...")
    subprocess.Popen(["./venv/bin/python", "chess_final.py"])
    print("[DONE] Gata, boss! Acceseaza http://192.168.0.125:5005")

if __name__ == "__main__":
    main()
