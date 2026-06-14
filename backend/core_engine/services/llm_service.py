import os
import httpx
import json
import re
import asyncio
from typing import Optional, Dict, Any, Union

# URL pentru Ollama (folosind numele de rețea Docker 'llm')
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://llm:11434")

class LLMService:
    """Serviciu asincron pentru interacțiunea cu Ollama."""
    
    def __init__(self, timeout: int = 1800):
        # Time-out generos pentru modele mari (Gemma 4-E4B, Qwen 3.6)
        self.timeout = httpx.Timeout(timeout, connect=10.0)
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def close(self):
        await self.client.aclose()

    async def generate(self, prompt: str, model: str, is_json: bool = False, provider: str = "ollama") -> Union[str, Dict[str, Any]]:
        """Interfață asincronă pentru generare text/JSON."""
        # Ignorăm provider-ul pentru acest test și folosim Ollama peste tot
        return await self._send_to_ollama(model, prompt, is_json)

    async def _send_to_ollama(self, model: str, prompt: str, is_json: bool) -> Union[str, Dict[str, Any]]:
        """Apel asincron către API-ul Ollama (/api/generate)."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_ctx": 16384
            }
        }
        if is_json:
            payload["format"] = "json"

        try:
            resp = await self.client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            resp.raise_for_status()
            raw = resp.json().get("response", "")
            
            if is_json:
                return self._parse_json(raw)
            return raw
        except Exception as e:
            print(f"[!] Eroare Ollama Async Service: {e}")
            return {} if is_json else ""

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parsare robustă pentru răspunsuri AI care pot conține zgomot (e.g. <think>)."""
        # 1. Curățăm eventuale tag-uri de gândire (DeepSeek style)
        clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # 2. Curățăm Markdown code blocks
        clean = re.sub(r'```json\s*|\s*```', '', clean, flags=re.DOTALL).strip()
        
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            # Încercăm să extragem primul obiect JSON valid { ... }
            match = re.search(r'\{.*\}', clean, re.DOTALL)
            if match:
                try: return json.loads(match.group(0))
                except: pass
        return {}
