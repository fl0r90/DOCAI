import ollama
import subprocess
import os

def main():
    client = ollama.Client(host='http://localhost:11434')
    prompt = """Creeaza o aplicatie Flask completa intr-un singur fisier numit 'chess_fixed_v2.py'. 
    FRONTEND (FOARTE IMPORTANT):
    - Foloseste un DIV cu id='board' si STYLE='width: 400px; margin: auto;'.
    - Foloseste Chessboard.js de pe CDN.
    - MODIFICA 'pieceTheme' sa foloseasca acest URL: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png'.
    - Adauga logica de 'onDrop' care sa trimita mutarea la server prin AJAX (POST /move).
    - Foloseste JQuery de pe CDN.

    BACKEND:
    - Foloseste python-chess.
    - Mentine starea partidei intr-un obiect global 'board = chess.Board()'.
    - Ruta '/move' primeste mutarea (format UCI), o aplica, si raspunde cu mutarea AI-ului (random valida).
    
    IMPORTANT: Scrie DOAR codul Python curat, fara explicatii. Sa fie GATA de rulat pe portul 5005."""
    
    print("[*] Generam varianta vizibila...")
    resp = client.generate(model='qwen2.5-coder:7b', prompt=prompt)
    code = resp['response'].strip()
    
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()

    with open("chess_fixed_v2.py", "w") as f:
        f.write(code)
    
    print("[*] Pornim serverul...")
    subprocess.run("fuser -k 5005/tcp", shell=True)
    subprocess.Popen(["/home/cfp_90/monitor_test/venv/bin/python", "chess_fixed_v2.py"])
    print("[DONE] Acum ar trebui sa se vada! http://192.168.0.125:5005")

if __name__ == "__main__":
    main()
