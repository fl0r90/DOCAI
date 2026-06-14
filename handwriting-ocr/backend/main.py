import os
import shutil
import uuid
import json
import base64
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pdf2image import convert_from_path
from PIL import Image
from io import BytesIO

app = FastAPI(title="Handwriting OCR Quad-Scan (Llama-3.2-Vision)")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://v2-llm-1:11434")

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def transcribe_fragment(image_pil, label=""):
    """Transcrie un fragment de imagine la rezoluție mare."""
    buffered = BytesIO()
    image_pil.convert("RGB").save(buffered, format="JPEG", quality=95)
    img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    prompt = f"Ești un expert paleograf. Transcrie acest fragment de manuscris în limba ROMÂNĂ. Returnează DOAR textul transcris din acest fragment ({label}). Fără nicio introducere."
    
    payload = {
        "model": "llama3.2-vision",
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0},
        "images": [img_b64]
    }
    
    try:
        res = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=600)
        res.raise_for_status()
        return res.json().get("response", "").strip()
    except Exception as e:
        return f"[Eroare Fragment]: {str(e)}"

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    extension = file.filename.split(".")[-1].lower()
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.{extension}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        if extension == "pdf":
            # Pentru PDF facem pagină cu pagină, dar fără slicing (deocamdată)
            images = convert_from_path(file_path, dpi=300)
            final_text = []
            for i, img in enumerate(images):
                txt = transcribe_fragment(img, f"Pagina {i+1}")
                final_text.append(f"--- Pagina {i+1} ---\n{txt}")
            output = "\n\n".join(final_text)
        elif extension in ["jpg", "jpeg", "png"]:
            img = Image.open(file_path).convert("RGB")
            w, h = img.size
            
            # TRIPLE STRIP SCAN (High Detail)
            # Slicing with 20% overlap to avoid cutting lines
            strip_h = int(h / 2.5) 
            
            parts = [
                (img.crop((0, 0, w, strip_h + 50)), "Partea de Sus"),
                (img.crop((0, int(h/2) - strip_h//2, w, int(h/2) + strip_h//2)), "Partea de Mijloc"),
                (img.crop((0, h - strip_h - 50, w, h)), "Partea de Jos")
            ]
            
            results = []
            for i, (p_img, label) in enumerate(parts):
                print(f"[*] Scanare {label}...")
                txt = transcribe_fragment(p_img, label)
                results.append(txt)
            
            # Mergem rezultatele (încercăm să eliminăm dublurile evidente la îmbinare prin prompt final sau simplu join)
            raw_combined = "\n".join(results)
            
            # Final Clean-up cu un model de text (opțional, dar bun pentru eliminat dublurile de la overlap)
            print("[*] Finalizare și curățare text...")
            final_prompt = f"Mai jos sunt fragmente transcrise dintr-o pagină. Combină-le într-un text coerent în limba ROMÂNĂ, eliminând repetările cauzate de suprapunerea fragmentelor. Păstrează doar textul curat.\n\n{raw_combined}"
            
            output = requests.post(f"{OLLAMA_URL}/api/generate", json={
                "model": "gemma2:2b",
                "prompt": final_prompt,
                "stream": False,
                "options": {"temperature": 0.0}
            }, timeout=300).json().get("response", "").strip()
            
        else:
            raise HTTPException(status_code=400, detail="Format nesuportat")
            
        print(f"[*] REZULTAT QUAD-SCAN:\n{output}\n" + "="*50)
        return {"text": output, "filename": file.filename}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app.get("/health")
def health():
    return {"status": "ok", "engine": "Triple-Strip QuadScan + Gemma2 Cleanup"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
