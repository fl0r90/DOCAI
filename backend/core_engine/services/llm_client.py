import os
import json
import re
import requests
import httpx
from typing import Dict, Any, List, Optional, Union
from ..core.config import get_llm_config

class UnifiedLLMClient:
    """Client agnostic unificat pentru inferență LLM.
    Suportă 3 motoare:
      - 'ollama': API-ul nativ Ollama (/api/chat, /api/generate)
      - 'vllm': API compatibil OpenAI (/v1/chat/completions)
      - 'lmstudio': API compatibil OpenAI (/v1/chat/completions) fie pe host, fie pe stație remote.
    """

    @staticmethod
    def get_engine_config() -> Dict[str, Any]:
        return get_llm_config()

    @classmethod
    def _normalize_tool_calls(cls, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalizează tool_calls astfel încât arguments să fie un dicționar Python."""
        normalized = []
        for idx, tc in enumerate(tool_calls or []):
            fn = tc.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments", {})
            call_id = tc.get("id") or f"call_{idx}_{name}"
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    pass
            normalized.append({
                "id": call_id,
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": args
                }
            })
        return normalized

    @classmethod
    def _to_openai_tools(cls, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convertește lista de unelte în schema standard OpenAI function-calling."""
        openai_tools = []
        for t in tools or []:
            if "function" in t:
                openai_tools.append(t)
            elif "name" in t:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("parameters", {"type": "object", "properties": {}})
                    }
                })
        return openai_tools

    @classmethod
    def chat_step(cls, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] = None, 
                  model: Optional[str] = None, temperature: float = 0.0, num_ctx: int = 32768) -> Dict[str, Any]:
        """Efectuează un pas sincron de chat/raționament cu suport complet pentru tool-use.
        Returnează:
          {
            "content": str,
            "tool_calls": List[dict],
            "raw": dict
          }
        """
        cfg = cls.get_engine_config()
        engine = cfg.get("active_llm_engine", "ollama").lower()
        active_model = model or cfg.get("active_model", "qwen3.6:35b-a3b")

        if engine == "lmstudio":
            base_url = cfg.get("lmstudio_url") or os.getenv("LMSTUDIO_URL", "http://host.docker.internal:1234/v1")
            base_url = base_url.rstrip("/")
            url = f"{base_url}/chat/completions"
            headers = {"Content-Type": "application/json"}
            api_key = (cfg.get("lmstudio_api_key") or "").strip()
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            payload: Dict[str, Any] = {
                "model": active_model,
                "messages": messages,
                "temperature": temperature,
            }
            if tools:
                payload["tools"] = cls._to_openai_tools(tools)
                payload["tool_choice"] = "auto"

            timeout = cfg.get("lmstudio_timeout", 300)
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            choice = (data.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            
            content = msg.get("content") or ""
            tool_calls = cls._normalize_tool_calls(msg.get("tool_calls") or [])
            return {"content": content, "tool_calls": tool_calls, "raw": msg}

        elif engine == "vllm":
            vllm_url = os.getenv("VLLM_URL", "http://vllm:8000/v1").rstrip("/")
            url = f"{vllm_url}/chat/completions"
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": active_model,
                "messages": messages,
                "temperature": temperature,
            }
            if tools:
                payload["tools"] = cls._to_openai_tools(tools)
            resp = requests.post(url, json=payload, headers=headers, timeout=300)
            resp.raise_for_status()
            data = resp.json()
            choice = (data.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            content = msg.get("content") or ""
            tool_calls = cls._normalize_tool_calls(msg.get("tool_calls") or [])
            return {"content": content, "tool_calls": tool_calls, "raw": msg}

        else:
            # Implicit: Ollama
            ollama_url = os.getenv("OLLAMA_URL", "http://llm:11434").rstrip("/")
            url = f"{ollama_url}/api/chat"
            payload = {
                "model": active_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_ctx": num_ctx
                }
            }
            if tools:
                payload["tools"] = tools

            resp = requests.post(url, json=payload, timeout=1800)
            resp.raise_for_status()
            data = resp.json()
            msg = data.get("message") or {}
            content = msg.get("content") or ""
            tool_calls = cls._normalize_tool_calls(msg.get("tool_calls") or [])
            return {"content": content, "tool_calls": tool_calls, "raw": msg}

    @classmethod
    async def async_generate(cls, prompt: str, model: Optional[str] = None, 
                             is_json: bool = False, temperature: float = 0.1, 
                             timeout: int = 180) -> Union[str, Dict[str, Any]]:
        """Generare asincronă utilizată de Grinder / Document Processor."""
        cfg = cls.get_engine_config()
        engine = cfg.get("active_llm_engine", "ollama").lower()
        active_model = model or cfg.get("specialist_tabular") or cfg.get("active_model", "gemma4:e4b")

        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
            if engine in ["lmstudio", "vllm"]:
                if engine == "lmstudio":
                    base_url = cfg.get("lmstudio_url") or os.getenv("LMSTUDIO_URL", "http://host.docker.internal:1234/v1")
                    api_key = (cfg.get("lmstudio_api_key") or "").strip()
                else:
                    base_url = os.getenv("VLLM_URL", "http://vllm:8000/v1")
                    api_key = ""

                base_url = base_url.rstrip("/")
                url = f"{base_url}/chat/completions"
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                payload: Dict[str, Any] = {
                    "model": active_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                }
                if is_json:
                    payload["response_format"] = {"type": "json_object"}

                try:
                    resp = await client.post(url, json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    choice = (data.get("choices") or [{}])[0]
                    raw_text = (choice.get("message") or {}).get("content", "")
                    if is_json:
                        return cls._parse_json(raw_text)
                    return raw_text
                except Exception as ex:
                    print(f"[!] Eroare async {engine} generation: {ex}")
                    if is_json and "response_format" in payload:
                        try:
                            del payload["response_format"]
                            resp = await client.post(url, json=payload, headers=headers)
                            resp.raise_for_status()
                            raw_text = (resp.json().get("choices", [{}])[0].get("message") or {}).get("content", "")
                            return cls._parse_json(raw_text)
                        except Exception:
                            pass
                    return {} if is_json else ""

            else:
                # Ollama /api/generate
                ollama_url = os.getenv("OLLAMA_URL", "http://llm:11434").rstrip("/")
                url = f"{ollama_url}/api/generate"
                payload = {
                    "model": active_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_ctx": 16384
                    }
                }
                if is_json:
                    payload["format"] = "json"

                try:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    raw = resp.json().get("response", "")
                    if is_json:
                        return cls._parse_json(raw)
                    return raw
                except Exception as ex:
                    print(f"[!] Eroare async Ollama generation: {ex}")
                    return {} if is_json else ""

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        """Curăță tag-urile <think> și blocurile markdown pentru a extrage JSON valid."""
        clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        clean = re.sub(r'```json\s*|\s*```', '', clean, flags=re.DOTALL).strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', clean, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        return {}
