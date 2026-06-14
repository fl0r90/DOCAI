import ollama
import subprocess
import os

def main():
    client = ollama.Client(host='http://localhost:11434')
    prompt = """Creeaza o aplicatie Flask intr-un singur fisier numit 'chess_fixed.py'. 
    Trebuie sa contina:
    1. Importurile: flask, chess (din python-chess).
    2. HTML-ul complet inclus intr-o variabila string (foloseste chessboard.js si jquery de pe CDN).
    3. O ruta '/' care returneaza HTML-ul respectiv.
    4. O ruta '/move' care primeste o mutare in format SAN sau UCI, o aplica pe tabla si raspunde cu mutarea AI-ului (foloseste un algoritm simplu de evaluare sau alege o mutare valida random).
    5. Serverul sa ruleze pe 0.0.0.0:5005.
    
    IMPORTANT: Scrie DOAR codul Python, fara explicatii, fara backticks (```), fara tag-uri. Incepe direct cu 'from flask import...'."""
    
    print("[*] Cerem codul curat de la Qwen...")
    resp = client.generate(model='qwen2.5-coder:7b', prompt=prompt)
    code = resp['response'].strip()
    
    # Clean up any potential markdown or garbage
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()
    
    # Final check for garbage at start
    lines = code.split('\n')
    while lines and not lines[0].startswith(('from', 'import', '#', 'app =')):
        lines.pop(0)
    code = '\n'.join(lines)

    with open("chess_fixed.py", "w") as f:
        f.write(code)
    
    print("[*] Pornim serverul...")
    # Kill any old process on 5005
    subprocess.run("fuser -k 5005/tcp", shell=True)
    subprocess.Popen(["/home/cfp_90/monitor_test/venv/bin/python", "chess_fixed.py"])
    print("[DONE] Verifica http://192.168.0.125:5005")

if __name__ == "__main__":
    main()
