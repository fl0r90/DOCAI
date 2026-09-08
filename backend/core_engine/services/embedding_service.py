import os
import requests
from typing import Optional, List

class EmbeddingService:
    """
    Serviciu unificat de embeddings (Forensic DocAI v0.7.0):
    - Mod 'ollama': folosește containerul Ollama (/api/embeddings, model bge-m3)
    - Mod 'lmstudio' / 'openai': folosește endpoint-ul OpenAI-compatible /v1/embeddings
    - Mod 'cpu': folosește sentence_transformers pe CPU pentru a elibera 100% din memoria GPU (0 VRAM)
    """
    _cpu_model = None

    @classmethod
    def get_embedding(cls, text_input: str, model: str = "bge-m3") -> Optional[List[float]]:
        if not text_input or not text_input.strip():
            return None

        engine = os.getenv("EMBEDDING_ENGINE", "ollama").lower()
        
        # 1. CPU Mode (Zero VRAM)
        if engine in ["cpu", "sentence_transformers", "local"]:
            try:
                if cls._cpu_model is None:
                    from sentence_transformers import SentenceTransformer
                    model_path = os.getenv("EMBEDDING_LOCAL_PATH", "BAAI/bge-m3")
                    cls._cpu_model = SentenceTransformer(model_path, device="cpu")
                emb = cls._cpu_model.encode(text_input, normalize_embeddings=True)
                return emb.tolist()
            except Exception as e:
                print(f"[!] CPU Embedding error, falling back to Ollama: {e}")

        # 2. OpenAI / LM Studio Mode (/v1/embeddings)
        if engine in ["lmstudio", "openai"]:
            try:
                url = os.getenv("LMSTUDIO_URL", "http://host.docker.internal:1234/v1").rstrip("/")
                emb_url = f"{url}/embeddings"
                headers = {}
                api_key = os.getenv("LMSTUDIO_API_KEY", "")
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                res = requests.post(emb_url, headers=headers, json={"model": model, "input": text_input[:4000]}, timeout=30)
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("data", [])
                    if items and "embedding" in items[0]:
                        return items[0]["embedding"]
            except Exception as e:
                print(f"[!] LM Studio Embedding error, falling back to Ollama: {e}")

        # 3. Default: Ollama (/api/embeddings)
        try:
            ollama_url = os.getenv("OLLAMA_URL", "http://llm:11434").rstrip("/")
            res = requests.post(
                f"{ollama_url}/api/embeddings",
                json={"model": "bge-m3", "prompt": text_input[:4000], "keep_alive": 300},
                timeout=30
            )
            if res.status_code == 200:
                emb = res.json().get("embedding")
                if emb:
                    return emb
        except Exception as e:
            print(f"[!] Ollama Embedding error: {e}")

        # 4. Automatic Resilient Fallback: CPU SentenceTransformers (Zero Configuration)
        try:
            if cls._cpu_model is None:
                from sentence_transformers import SentenceTransformer
                model_path = os.getenv("EMBEDDING_LOCAL_PATH", "BAAI/bge-m3")
                cls._cpu_model = SentenceTransformer(model_path, device="cpu")
            emb = cls._cpu_model.encode(text_input, normalize_embeddings=True)
            return emb.tolist()
        except Exception as e:
            print(f"[!] CPU Fallback Embedding error: {e}")

        return None

embedding_service = EmbeddingService()
