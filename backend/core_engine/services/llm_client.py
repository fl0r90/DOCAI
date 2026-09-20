import os
import json
import re
import time
import queue
import threading
import logging
import requests
import httpx
from typing import Callable, Dict, Any, List, Optional, Union
from ..core.config import get_llm_config
from .debug_logger import debug_logger

logger = logging.getLogger(__name__)


def _normalize_ollama_model_name(model_name: str) -> str:
    """
    Normalize Ollama model names to ensure they use the correct format.
    
    Ollama uses 'model:tag' format (colon separator). This function handles
    common variations where users might enter 'model-tag' (dash separator)
    or other formats, converting them to the proper colon-separated format.
    
    Examples:
        'qwen3.8-27b' -> 'qwen3.8:27b'
        'gemma4-26b' -> 'gemma4:26b'
        'deepseek-r1-distill-qwen-14b-awq' -> 'deepseek-r1-distill-qwen-14b:awq'
    
    Args:
        model_name: The model name to normalize
        
    Returns:
        Normalized model name using colon separator for tag
    """
    if not model_name:
        return model_name

    # Eliminăm prefixul de organizație dacă există (ex: google/gemma-4-e4b -> gemma-4-e4b)
    cleaned = model_name.split("/")[-1].strip()

    # Mapări robuste pentru alias-urile populare
    cleaned_lower = cleaned.lower()
    if cleaned_lower in ["gemma-4-e4b", "gemma4-e4b", "gemma4e4b", "gemma-4:e4b"]:
        return "gemma4:e4b"
    if cleaned_lower in ["gemma-4-e2b", "gemma4-e2b", "gemma4e2b", "gemma-4:e2b"]:
        return "gemma4:e2b"
    if cleaned_lower in ["qwen3.8", "qwen-3.8", "qwen-3-8"]:
        return "qwen3.8:latest"

    if ':' in cleaned:
        return cleaned
    
    # Pattern: potrivire sufix parametri (ex: -27b, -e4b, -latest, -instruct)
    pattern = r'^(.+)-(e\d+[bB]|\d+[bB](?:-[a-zA-Z0-9_]+)?|latest|instruct|chat|text|awq)$'
    match = re.match(pattern, cleaned, re.IGNORECASE)
    
    if match:
        base = match.group(1).replace("-", "")
        tag = match.group(2)
        normalized = f"{base}:{tag}"
        logger.debug(f"Normalized model name: {model_name} -> {normalized}")
        return normalized
    
    return cleaned


class ChatStoppedError(Exception):
    """Semnal intern: utilizatorul a cerut oprirea generării în timpul unui apel LLM."""
    pass


def _iter_stream_lines(resp, stop_check: Optional[Callable[[], bool]] = None):
    """Parcurge liniile NDJSON dintr-un răspuns stream Ollama.

    Un thread de citire pune liniile într-o coadă; bucla principală o poll-uiește
    la ~1s, astfel încât stop_check se verifică constant — inclusiv în perioadele
    lungi fără date (încărcare model / prefill). Dacă stop_check devine True,
    ridică ChatStoppedError; apelantul închide resp și slotul server-side se abortează.
    """
    q: "queue.Queue" = queue.Queue()

    def _reader():
        try:
            for line in resp.iter_lines():
                q.put(line)
        except Exception as exc:
            q.put(exc)
        finally:
            q.put(None)

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    while True:
        if stop_check and stop_check():
            raise ChatStoppedError("Stop request received during LLM streaming.")
        try:
            item = q.get(timeout=1.0)
        except queue.Empty:
            continue
        if item is None:
            return
        if isinstance(item, Exception):
            raise item
        yield item


class UnifiedLLMClient:
    """Client agnostic unificat pentru inferență LLM.
    Suportă 3 motoare:
      - 'ollama': API-ul nativ Ollama (/api/chat, /api/generate)
      - 'vllm': API compatibil OpenAI (/v1/chat/completions)
      - 'lmstudio': API compatibil OpenAI (/v1/chat/completions) fie pe host, fie pe stație remote.

    ## Tool Calls & Ollama Compatibility

    **Problem**: Ollama's native `/api/chat` endpoint expects `tool_calls[*].function.arguments`
    as a parsed JSON object (dict), NOT as an escaped JSON string. When arguments arrive as
    a string (e.g., `"arguments": "{\"key\": \"val\"}"`), the Go-based parser fails with:
    `400 Bad Request: "Value looks like object, but can't find closing '}' symbol"`

    **Solution**: This client implements automatic sanitization and normalization:

    1. **For Ollama native (`/api/chat`)**:
       - `_sanitize_message_for_ollama()`: Converts string args → dict (or {} on error)
       - Ensures all tool_call arguments are proper Python dicts before sending

    2. **For OpenAI-compatible endpoints** (`/v1/chat/completions`):
       - `_to_openai_messages()`: Converts dict args → JSON string
       - Handles tool_call_id pairing and orphan removal

    3. **Automatic fallback**: On 400 error from `/api/chat`, automatically retries via
       `/v1/chat/completions` (configurable via `OLLAMA_API_MODE` env var or config key)

    See: test_ollama_toolcall_fix.py for comprehensive tests.
    """

    @staticmethod
    def get_engine_config() -> Dict[str, Any]:
        return get_llm_config()

    @classmethod
    def _normalize_tool_calls(cls, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalizează tool_calls astfel încât arguments să fie un dicționar Python valid,
        desfăcând JSON-uri multiple concatenate generate de streaming (ex: Qwen/Ollama)."""
        normalized = []
        for idx, tc in enumerate(tool_calls or []):
            fn = tc.get("function", {})
            name = fn.get("name", "")
            # Curățăm repetiții dacă numele a fost concatenat în streaming (ex: SEARCH_TEXTSEARCH_TEXT)
            rep_match = re.match(r"^([A-Za-z0-9_]+?)\1+$", name)
            if rep_match:
                name = rep_match.group(1)
            
            args = fn.get("arguments", {})
            parsed_args_list = []
            if isinstance(args, str):
                raw_args = args.strip()
                if raw_args:
                    decoder = json.JSONDecoder()
                    pos = 0
                    while pos < len(raw_args):
                        while pos < len(raw_args) and raw_args[pos].isspace():
                            pos += 1
                        if pos >= len(raw_args):
                            break
                        try:
                            obj, end = decoder.raw_decode(raw_args, idx=pos)
                            if isinstance(obj, dict):
                                parsed_args_list.append(obj)
                            pos = end
                        except Exception:
                            break
                if not parsed_args_list:
                    parsed_args_list = [{}]
            elif isinstance(args, dict):
                parsed_args_list = [args]
            else:
                parsed_args_list = [{}]

            for sub_idx, p_args in enumerate(parsed_args_list):
                call_id = f"call_{len(normalized)}_{name}"
                normalized.append({
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": p_args
                    }
                })
        return normalized

    @classmethod
    def _coerce_tool_arguments(cls, args: Any) -> Dict[str, Any]:
        """Returnează argumentele unui tool_call ca dict.

        Ollama /api/chat respinge cu 400 ("Value looks like object, but can't find
        closing '}' symbol") orice arguments care nu e un obiect JSON. Acceptăm:
          - dict            -> se păstrează
          - string JSON     -> se parsează; dacă rezultă dict, îl folosim
          - string neparabil / orice alt tip -> {} (fail-safe, fără crash)

        **Purpose**: Fail-safe conversion to ensure tool_call arguments are always
        valid Python dicts before sending to Ollama /api/chat endpoint.

        Args:
            args: Tool call arguments (string JSON, dict, or other type)

        Returns:
            Dict if parsing succeeds or input is already a dict; {} otherwise
        """
        if isinstance(args, dict):
            return args
        if isinstance(args, str):
            try:
                parsed = json.loads(args)
            except (json.JSONDecodeError, TypeError, ValueError):
                return {}
            return parsed if isinstance(parsed, dict) else {}
        # list, int, bool, None, etc.
        return {}

    @classmethod
    def _sanitize_message_for_ollama(cls, message: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitizează un mesaj înainte de trimiterea către Ollama /api/chat.

        Ollama așteaptă ca tool_calls['function']['arguments'] să fie un dict/object,
        nu un string JSON. Dacă arguments este string, îl parsează în dict (sau {} la eroare).

        **Purpose**: Prevents 400 Bad Request errors from Ollama's native /api/chat endpoint
        which expects tool_call arguments as parsed JSON objects, not escaped strings.

        **Example**:
            Input:  {"function": {"arguments": '{"key": "val"}'}}
            Output: {"function": {"arguments": {"key": "val"}}}

        Args:
            message: Message dict potentially containing tool_calls with string args

        Returns:
            Sanitized message with all tool_call arguments as Python dicts
        """
        sanitized = dict(message) if isinstance(message, dict) else {}
        # content: null eșuează la unmarshaling în structul Go al Ollamei -> ""
        if sanitized.get("content") is None:
            sanitized["content"] = ""
        if "tool_calls" in sanitized and isinstance(sanitized["tool_calls"], list):
            normalized_tool_calls = []
            for tc in sanitized["tool_calls"]:
                tc_copy = tc.copy() if isinstance(tc, dict) else {}
                fn = tc_copy.get("function")
                fn_copy = fn.copy() if isinstance(fn, dict) else {}

                # arguments trebuie să fie întotdeauna un dict valid
                fn_copy["arguments"] = cls._coerce_tool_arguments(fn_copy.get("arguments"))

                # name trebuie să fie un string (endpoint-ul nativ e strict)
                if not isinstance(fn_copy.get("name"), str):
                    fn_copy["name"] = str(fn_copy.get("name") or "")

                tc_copy["function"] = fn_copy

                # id opțional dar recomandat; păstrăm dacă e string
                if "id" not in tc_copy or not isinstance(tc_copy.get("id"), str):
                    tc_copy.setdefault("id", "")

                normalized_tool_calls.append(tc_copy)
            sanitized["tool_calls"] = normalized_tool_calls
        return sanitized

    @classmethod
    def _sanitize_messages_for_ollama(cls, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sanitizează o listă de mesaje pentru compatibilitate cu Ollama /api/chat.

        Elimină și mesajele orfane cu role "tool": trunchierea istoricului
        (truncate_messages) poate tăia mesajul assistant cu tool_calls pe care se
        referă un rezultat de tool; un astfel de mesaj orfan e respins de
        endpoint-urile OpenAI-compatibile (400 invalid tool call).

        **Purpose**: 
        - Converts all tool_call arguments from strings to dicts
        - Removes orphaned 'tool' messages that would cause 400 errors

        Args:
            messages: List of conversation message dicts

        Returns:
            Sanitized list with dict args and no orphaned tool messages
        """
        if not messages:
            return messages
        cleaned = [cls._sanitize_message_for_ollama(msg) for msg in messages]
        result: List[Dict[str, Any]] = []
        for i, msg in enumerate(cleaned):
            if msg.get("role") == "tool":
                prev = cleaned[i - 1] if i > 0 else None
                if not (isinstance(prev, dict) and prev.get("role") == "assistant" and prev.get("tool_calls")):
                    logger.warning("[OLLAMA_SANITIZE] eliminat mesaj 'tool' orfan (fără tool_calls assistant anterior)")
                    continue
            result.append(msg)
        return result

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
    def _to_openai_messages(cls, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convertește formatul intern al conversației în format OpenAI /v1/chat/completions.

        Inversarea conversiei față de _sanitize_messages_for_ollama: endpoint-urile
        OpenAI-compatibile (vLLM, LM Studio, Ollama /v1) așteaptă
        tool_calls[*].function.arguments ca string JSON serializat.
        Mesajele de rol "tool" primesc tool_call_id împerecheat (FIFO) cu
        tool_call-urile mesajului assistant anterior; mesajele orfane sunt eliminate.

        **Purpose**:
        - Converts all tool_call arguments from dicts to JSON strings for OpenAI compatibility
        - Assigns tool_call_id to 'tool' messages for proper pairing with assistant calls
        - Removes orphaned tool messages that would cause 400 errors

        Args:
            messages: List of conversation message dicts (with dict args)

        Returns:
            OpenAI-compatible list with string args and paired tool_call_ids
        """
        out: List[Dict[str, Any]] = []
        pending_ids: List[str] = []
        for m in messages or []:
            if not isinstance(m, dict):
                continue
            role = m.get("role")
            if role not in ("system", "user", "assistant", "tool"):
                continue
            m2 = dict(m)
            if m2.get("content") is None:
                m2["content"] = ""
            if role == "assistant":
                pending_ids = []
                tool_calls = m2.get("tool_calls")
                if isinstance(tool_calls, list) and tool_calls:
                    normalized: List[Dict[str, Any]] = []
                    for idx, tc in enumerate(tool_calls):
                        tc2 = dict(tc) if isinstance(tc, dict) else {}
                        fn = dict(tc2.get("function") or {})
                        args = fn.get("arguments")
                        if isinstance(args, (dict, list)):
                            try:
                                fn["arguments"] = json.dumps(args, ensure_ascii=False)
                            except (TypeError, ValueError):
                                fn["arguments"] = "{}"
                        elif args is None:
                            fn["arguments"] = "{}"
                        if not isinstance(fn.get("name"), str) or not fn.get("name"):
                            fn["name"] = str(fn.get("name") or "")
                        tc2["function"] = fn
                        tc2.setdefault("type", "function")
                        if not isinstance(tc2.get("id"), str) or not tc2.get("id"):
                            tc2["id"] = f"call_{idx}_{fn.get('name', '')}"
                        normalized.append(tc2)
                        pending_ids.append(tc2["id"])
                    m2["tool_calls"] = normalized
                elif not isinstance(tool_calls, list):
                    m2.pop("tool_calls", None)
                out.append(m2)
            elif role == "tool":
                tool_call_id = m2.get("tool_call_id") or (pending_ids.pop(0) if pending_ids else "")
                if not tool_call_id:
                    logger.warning("[OPENAI_MSGS] eliminat mesaj 'tool' orfan (fără tool_call_id asociat)")
                    continue
                m2["tool_call_id"] = tool_call_id
                out.append(m2)
            else:
                out.append(m2)
        if not out:
            out = [{"role": "user", "content": "Hello"}]
        return out

    @staticmethod
    def _ollama_api_mode(cfg: Dict[str, Any]) -> str:
        """Modul de API pentru Ollama: 'native' (/api/chat) sau 'openai' (/v1/chat/completions).

        Se setează prin cheia de config `ollama_api_mode` sau env OLLAMA_API_MODE
        (valori acceptate pentru modul OpenAI: openai | compat | compatible | v1 | 1 | true).
        Default: 'native'.
        """
        raw = cfg.get("ollama_api_mode") or os.getenv("OLLAMA_API_MODE", "")
        raw = str(raw).strip().lower()
        if raw in ("openai", "openai_compat", "openai-compat", "compat", "compatible", "v1", "1", "true", "yes"):
            return "openai"
        return "native"

    @classmethod
    def _chat_step_ollama_openai(cls, ollama_url: str, active_model: str,
                                 messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] = None,
                                 temperature: float = 0.0, num_ctx: int = 32768,
                                 stop_check: Optional[Callable[[], bool]] = None,
                                 fallback_reason: Optional[str] = None,
                                 format: Optional[Union[str, dict]] = None,
                                 max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Pas de chat prin endpoint-ul Ollama compatibil OpenAI (/v1/chat/completions).

        Alternativă la /api/chat pentru cazurile în care parserul nativ respinge
        formatul tool_calls (ex. 400 "Value looks like object, but can't find closing
        '}' symbol"). Răspunsul este convertit înapoi în formatul intern al aplicației
        (arguments -> dict) prin _normalize_tool_calls.

        **Purpose**: Provides OpenAI-compatible interface when Ollama native endpoint
        fails due to tool_call argument parsing issues. Automatically used via:
        - Config: `ollama_api_mode: "openai"` 
        - Env var: `OLLAMA_API_MODE=openai`
        - Fallback: On 400 error from /api/chat

        Args:
            ollama_url: Base URL (e.g., "http://llm:11434")
            active_model: Model name to use
            messages: Conversation history (dict args)
            tools: Optional list of tool definitions
            temperature: Sampling temperature
            num_ctx: Context window size
            stop_check: Optional callback to abort generation
            fallback_reason: Reason for using this endpoint (for logging)

        Returns:
            Dict with "content", "tool_calls" (dict args), and "raw" response
        """
        if stop_check and stop_check():
            raise ChatStoppedError("Stop request received.")
        url = f"{ollama_url}/v1/chat/completions"
        openai_messages = cls._to_openai_messages(messages)
        payload: Dict[str, Any] = {
            "model": active_model,
            "messages": openai_messages,
            "temperature": temperature,
            "stream": False,
        }
        if num_ctx:
            payload["options"] = {"num_ctx": num_ctx}
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = cls._to_openai_tools(tools)
            payload["tool_choice"] = "auto"
        if format:
            if format == "json":
                payload["response_format"] = {"type": "json_object"}
            elif isinstance(format, dict):
                payload["response_format"] = format

        print(f"[OLLAMA_OPENAI] POST {url} | model={active_model}, messages={len(openai_messages)}, tools={bool(tools)}")
        if fallback_reason:
            print(f"[OLLAMA_OPENAI] Fallback reason: {fallback_reason}")
            debug_logger.fallback_trigger(
                reason=fallback_reason,
                fallback_from="ollama_native",
                fallback_to="ollama_openai"
            )

        t_llm_start = time.time()
        est_tokens_in = sum(len(m.get("content") or "") for m in messages) // 3.5
        debug_logger.llm_call(
            model=active_model,
            endpoint=f"ollama_openai:{url}",
            payload_tokens_est=int(est_tokens_in),
            messages_count=len(messages)
        )

        try:
            resp = requests.post(url, json=payload, timeout=(10, 600))
            print(f"[OLLAMA_OPENAI_STATUS] HTTP {resp.status_code}")
            if resp.status_code != 200:
                print(f"[OLLAMA_OPENAI_ERROR_BODY] {resp.text[:1500]}")
            resp.raise_for_status()
        except requests.exceptions.RequestException as rex:
            err_body = getattr(resp, 'text', str(rex)) if 'resp' in locals() else str(rex)
            logger.error("[OLLAMA_OPENAI] %s | body: %.500s", rex, err_body)
            print(f"[OLLAMA_OPENAI_ERROR] {rex} | Response body: {err_body}")
            debug_logger.error("llm_client", "LLM_REQUEST_ERROR", str(rex), error_type="OllamaOpenAIError", details={"body": err_body[:500]})
            raise
        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        content = msg.get("content") or ""
        reasoning = msg.get("reasoning") or msg.get("reasoning_content") or ""
        if not content and reasoning:
            content = reasoning  # unele variante Qwen3.x răspund doar cu reasoning_content
        tool_calls = cls._normalize_tool_calls(msg.get("tool_calls") or [])
        print(f"[OLLAMA_OPENAI_RESULT] content_len={len(content)}, tool_calls_count={len(tool_calls)}")

        t_llm_dur = (time.time() - t_llm_start) * 1000
        debug_logger.llm_complete(
            model=active_model,
            duration_ms=t_llm_dur,
            tokens_out_est=int(len(content) // 3.5),
            tool_calls_count=len(tool_calls)
        )
        return {"content": content, "tool_calls": tool_calls, "raw": msg}

    @classmethod
    def chat_step(cls, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] = None,
                  model: Optional[str] = None, temperature: float = 0.0, num_ctx: int = 32768,
                  stop_check: Optional[Callable[[], bool]] = None,
                  format: Optional[Union[str, dict]] = None,
                  max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """Efectuează un pas sincron de chat/raționament cu suport complet pentru tool-use.

        `stop_check`: opțional, apelabil fără argumente; dacă returnează True în timpul
        generării (doar pe calea Ollama, care rulează în streaming), se închide conexiunea
        (abort server-side) și se ridică ChatStoppedError.

        Returnează:
          {
            "content": str,
            "tool_calls": List[dict],
            "raw": dict
          }
        """
        if stop_check and stop_check():
            raise ChatStoppedError("Stop request received.")
        cfg = cls.get_engine_config()
        engine = cfg.get("active_llm_engine", "ollama").lower()
        active_model = model or cfg.get("active_model") or os.getenv("ACTIVE_MODEL", "")
        
        # Normalize Ollama model names to handle common naming variations
        if engine == "ollama" and active_model:
            active_model = _normalize_ollama_model_name(active_model)

        t_llm_step_start = time.time()
        est_tokens_in = sum(len(m.get("content") or "") for m in messages) // 3.5
        debug_logger.llm_call(
            model=active_model,
            endpoint=engine,
            payload_tokens_est=int(est_tokens_in),
            messages_count=len(messages)
        )

        if engine == "lmstudio":
            if stop_check and stop_check():
                raise ChatStoppedError("Investigație oprită de utilizator.")

            base_url = cfg.get("lmstudio_url") or os.getenv("LMSTUDIO_URL", "http://host.docker.internal:1234/v1")
            base_url = base_url.rstrip("/")
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            url = f"{base_url}/chat/completions"
            headers = {"Content-Type": "application/json"}
            api_key = (cfg.get("lmstudio_api_key") or "").strip()
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            # LM Studio (OpenAI-compatibil) cere arguments ca string JSON și roluri valide;
            # _to_openai_messages face conversia, păstrează tool_calls/rolul "tool"
            # și elimină mesajele orfane.
            validated_messages = cls._to_openai_messages(messages)

            payload: Dict[str, Any] = {
                "model": active_model,
                "messages": validated_messages,
                "temperature": float(temperature),
                "stream": False,  # LM Studio / OpenAI-compatible endpoints expect stream=false for sync calls
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens
            if format:
                if format == "json":
                    payload["response_format"] = {"type": "json_object"}
                elif isinstance(format, dict):
                    payload["response_format"] = format
            # LM Studio may not support tools; omit if empty or invalid
            if tools:
                try:
                    payload["tools"] = cls._to_openai_tools(tools)
                    payload["tool_choice"] = "auto"
                except Exception:
                    pass  # fallback to no tools

            try:
                timeout_val = int(cfg.get("lmstudio_timeout", 300))
            except (ValueError, TypeError):
                timeout_val = 300

            payload_str = json.dumps(payload, ensure_ascii=False)[:2500]
            print(f"[LMSTUDIO] POST {url} | model={active_model}, messages={len(messages)}, tools={bool(tools)}, timeout={timeout_val}")
            print(f"[LMSTUDIO_PAYLOAD] {payload_str}")
            try:
                # Folosim timeout=(connect, read): 10s conectare, timeout_val generare
                resp = requests.post(url, json=payload, headers=headers, timeout=(10, timeout_val))
                print(f"[LMSTUDIO_STATUS] {resp.status_code}")
                if resp.status_code != 200:
                    err_body = resp.text[:1500]
                    print(f"[LMSTUDIO_ERROR_BODY] {err_body}")
                resp.raise_for_status()
            except Exception as e:
                err_body = getattr(resp, 'text', str(e)) if 'resp' in locals() else str(e)
                print(f"[LMSTUDIO_ERROR] {type(e).__name__}: {e} | Payload: {payload_str}")
                print(f"[LMSTUDIO_ERROR_RESPONSE] {err_body[:1500]}")
                raise

            data = resp.json()
            if "error" in data:
                err_detail = data["error"]
                err_msg = err_detail.get("message") if isinstance(err_detail, dict) else str(err_detail)
                raise RuntimeError(f"LM Studio API Error: {err_msg}")

            choice = (data.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            
            # LM Studio/Qwen3.8/Gemma may return reasoning_content instead of content
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
            tool_calls = cls._normalize_tool_calls(msg.get("tool_calls") or [])

            if not content and reasoning and not tool_calls:
                content = reasoning  # Folosim reasoning ca content doar dacă nu avem tool calls
            
            print(f"[LMSTUDIO_RESULT] content_len={len(content)}, reasoning_len={len(reasoning)}, tool_calls_count={len(tool_calls)}")
            t_llm_dur = (time.time() - t_llm_step_start) * 1000
            debug_logger.llm_complete(
                model=active_model,
                duration_ms=t_llm_dur,
                tokens_out_est=int(len(content) // 3.5),
                tool_calls_count=len(tool_calls)
            )
            return {"content": content, "tool_calls": tool_calls, "reasoning": reasoning, "raw": msg}

        elif engine == "vllm":
            vllm_url = os.getenv("VLLM_URL", "http://vllm:8000/v1").rstrip("/")
            url = f"{vllm_url}/chat/completions"
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": active_model,
                # vLLM (OpenAI-compatibil) cere arguments ca string JSON și roluri valide
                "messages": cls._to_openai_messages(messages),
                "temperature": temperature,
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens
            if tools:
                payload["tools"] = cls._to_openai_tools(tools)
            if format:
                if format == "json":
                    payload["response_format"] = {"type": "json_object"}
                elif isinstance(format, dict):
                    payload["response_format"] = format
            resp = requests.post(url, json=payload, headers=headers, timeout=300)
            resp.raise_for_status()
            data = resp.json()
            choice = (data.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            content = msg.get("content") or ""
            tool_calls = cls._normalize_tool_calls(msg.get("tool_calls") or [])
            return {"content": content, "tool_calls": tool_calls, "raw": msg}

        else:
            # Implicit: Ollama — streaming, cu verificare de stop la fiecare bucată.
            ollama_url = os.getenv("OLLAMA_URL", "http://llm:11434").rstrip("/")

            # Opțional: rutare prin endpoint-ul OpenAI-compatibil (OLLAMA_API_MODE=openai)
            if cls._ollama_api_mode(cfg) == "openai":
                return cls._chat_step_ollama_openai(
                    ollama_url=ollama_url, active_model=active_model, messages=messages,
                    tools=tools, temperature=temperature, num_ctx=num_ctx, stop_check=stop_check,
                    format=format, max_tokens=max_tokens,
                )

            url = f"{ollama_url}/api/chat"

            # Sanitize messages: convert tool_call arguments from string to dict if needed
            sanitized_messages = cls._sanitize_messages_for_ollama(messages)
            
            # Debug: log any tool_calls with string arguments that should have been sanitized
            for i, msg in enumerate(sanitized_messages):
                if "tool_calls" in msg:
                    for j, tc in enumerate(msg["tool_calls"]):
                        args = tc.get("function", {}).get("arguments")
                        if isinstance(args, str):
                            print(f"[DEBUG] UNSANITIZED STRING ARG at messages[{i}].tool_calls[{j}]: {args[:100]}...")
            
            opts: Dict[str, Any] = {
                "temperature": temperature,
                "num_ctx": num_ctx
            }
            if max_tokens:
                opts["num_predict"] = max_tokens

            payload = {
                "model": active_model,
                "messages": sanitized_messages,
                "stream": True,
                "truncate": False,
                "options": opts
            }
            if format:
                payload["format"] = format
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            roles_summary = [f"{m.get('role')}(len={len(m.get('content') or '')})" for m in sanitized_messages]
            
            # Debug: show tool_calls structure
            for i, msg in enumerate(sanitized_messages):
                if "tool_calls" in msg:
                    print(f"[OLLAMA_DEBUG] Message {i} ({msg.get('role')}): has {len(msg['tool_calls'])} tool calls")
                    for j, tc in enumerate(msg["tool_calls"]):
                        args = tc.get("function", {}).get("arguments")
                        args_type = type(args).__name__
                        print(f"[OLLAMA_DEBUG]   tool_call[{j}] arguments type={args_type}, value preview: {str(args)[:100]}...")
            
            payload_str = json.dumps(payload, ensure_ascii=False)
            print(f"[OLLAMA] POST {url} | model={active_model}, messages={len(sanitized_messages)}, tools={bool(tools)}")
            print(f"[OLLAMA_PAYLOAD_FULL] {payload_str[:3000]}")
            try:
                # timeout=(connect, read): read generos — încărcarea modelului rece + prefill-ul
                # unui prompt mare pot dura minute fără nicio dată pe socket. Verificarea stop-ului
                # în perioadele fără date o face _iter_stream_lines (poll la ~1s), nu timeout-ul.
                print(f"[OLLAMA] Sending request to {url} with timeout=(10, 600)...")
                resp = requests.post(url, json=payload, timeout=(10, 600))
                print(f"[OLLAMA_STATUS] HTTP {resp.status_code}")
                if resp.status_code == 400:
                    # Ollama /api/chat respinge cu 400 ("Value looks like object, but
                    # can't find closing '}' symbol") argumentele tool_calls care nu au
                    # reușit să fie sanitizate în dict. Încercăm o singură dată
                    # endpoint-ul compatibil OpenAI înainte de a eșua.
                    err_body = (resp.text or "")[:1500]
                    logger.warning("[OLLAMA] /api/chat 400 — fallback la /v1/chat/completions | %s", err_body)
                    print(f"[OLLAMA_FALLBACK] /api/chat a respins cererea (400): {err_body}")
                    print(f"[OLLAMA_FALLBACK] Reîncerc prin {ollama_url}/v1/chat/completions ...")
                    try:
                        resp.close()
                    except Exception:
                        pass
                    return cls._chat_step_ollama_openai(
                        ollama_url=ollama_url, active_model=active_model, messages=messages,
                        tools=tools, temperature=temperature, num_ctx=num_ctx, stop_check=stop_check,
                        fallback_reason=f"native /api/chat HTTP 400: {err_body}",
                        format=format,
                    )
                resp.raise_for_status()
            except requests.exceptions.RequestException as rex:
                err_body = getattr(resp, 'text', str(rex)) if 'resp' in locals() else str(rex)
                print(f"[OLLAMA_ERROR] timeout=(10,600) | {rex} | Response body: {err_body}")
                
                # Log the sanitized messages to see what we're actually sending
                print(f"[OLLAMA_ERROR_MESSAGES] Debugging messages being sent:")
                for i, msg in enumerate(sanitized_messages):
                    print(f"[OLLAMA_ERROR_MESSAGES]   [{i}] role={msg.get('role')}, content_len={len(msg.get('content', ''))}")
                    if "tool_calls" in msg:
                        for j, tc in enumerate(msg["tool_calls"]):
                            args = tc.get("function", {}).get("arguments")
                            print(f"[OLLAMA_ERROR_MESSAGES]       tool_call[{j}]: name={tc.get('function',{}).get('name')}, args_type={type(args).__name__}, args_preview={str(args)[:150]}...")
                
                try:
                    payload_dump = json.dumps(payload, ensure_ascii=False)
                    print(f"[OLLAMA_ERROR_DUMP] Full payload: {payload_dump[:3000]}")
                except Exception:
                    pass
                raise

            acc_content = ""
            acc_thinking = ""
            acc_tools: List[Dict[str, Any]] = []  # fiecare: {"name": str, "args_parts": [str]}

            def _merge_tool_call(tc: Dict[str, Any]) -> None:
                idx = tc.get("index")
                if not isinstance(idx, int):
                    idx = len(acc_tools) - 1 if acc_tools else 0
                while len(acc_tools) <= idx:
                    acc_tools.append({"name": "", "args_parts": []})
                fn = tc.get("function", {}) or {}
                name = fn.get("name")
                if isinstance(name, str):
                    if not acc_tools[idx]["name"]:
                        acc_tools[idx]["name"] = name
                    elif acc_tools[idx]["name"] != name and not name.startswith(acc_tools[idx]["name"]):
                        acc_tools[idx]["name"] += name
                args = fn.get("arguments")
                if args is not None:
                    if isinstance(args, str):
                        acc_tools[idx]["args_parts"].append(args)
                    else:
                        try:
                            acc_tools[idx]["args_parts"].append(json.dumps(args))
                        except Exception:
                            pass

            try:
                for raw_line in _iter_stream_lines(resp, stop_check):
                    if not raw_line:
                        continue
                    try:
                        chunk = json.loads(raw_line)
                    except (ValueError, TypeError):
                        continue
                    msg = chunk.get("message") or {}
                    piece = msg.get("content")
                    if isinstance(piece, str):
                        acc_content += piece
                    th_piece = msg.get("thinking")
                    if isinstance(th_piece, str):
                        acc_thinking += th_piece
                    for tc in (msg.get("tool_calls") or []):
                        _merge_tool_call(tc)
            finally:
                # Închiderea conexiunii abortează slotul server-side (eliberează CPU-ul).
                resp.close()

            # Dacă content este gol dar modelul a generat în thinking (ex: Qwen 3.5 / DeepSeek R1),
            # folosim reasoning-ul ca conținut pentru a nu pierde faptele extrase!
            if not acc_content.strip() and acc_thinking.strip() and not acc_tools:
                acc_content = acc_thinking.strip()

            tool_calls = cls._normalize_tool_calls([
                {
                    "id": f"call_{i}_{t['name']}",
                    "type": "function",
                    "function": {"name": t["name"], "arguments": "".join(t["args_parts"])}
                }
                for i, t in enumerate(acc_tools)
            ])
            t_llm_dur = (time.time() - t_llm_step_start) * 1000
            debug_logger.llm_complete(
                model=active_model,
                duration_ms=t_llm_dur,
                tokens_out_est=int(len(acc_content) // 3.5),
                tool_calls_count=len(tool_calls)
            )
            return {
                "content": acc_content,
                "tool_calls": tool_calls,
                "reasoning": acc_thinking.strip(),
                "raw": {"role": "assistant", "content": acc_content}
            }

    @classmethod
    async def async_generate(cls, prompt: str, model: Optional[str] = None, 
                             is_json: bool = False, temperature: float = 0.1, 
                             timeout: int = 180, max_tokens: Optional[int] = None) -> Union[str, Dict[str, Any]]:
        """Generare asincronă utilizată de Grinder / Document Processor."""
        cfg = cls.get_engine_config()
        engine = cfg.get("active_llm_engine", "ollama").lower()
        active_model = model or cfg.get("specialist_processing") or cfg.get("active_model") or os.getenv("ACTIVE_MODEL", "")
        
        # Normalize Ollama model names to handle common naming variations
        if engine == "ollama" and active_model:
            active_model = _normalize_ollama_model_name(active_model)

        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
            if engine in ["lmstudio", "vllm"]:
                if engine == "lmstudio":
                    base_url = cfg.get("lmstudio_url") or os.getenv("LMSTUDIO_URL", "http://host.docker.internal:1234/v1")
                    api_key = (cfg.get("lmstudio_api_key") or "").strip()
                else:
                    base_url = os.getenv("VLLM_URL", "http://vllm:8000/v1")
                    api_key = ""

                base_url = base_url.rstrip("/")
                if not base_url.endswith("/v1"):
                    base_url = f"{base_url}/v1"
                url = f"{base_url}/chat/completions"
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                payload: Dict[str, Any] = {
                    "model": active_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                }
                if max_tokens:
                    payload["max_tokens"] = max_tokens
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
                proc_ctx = int(cfg.get("processing_ctx") or cfg.get("narrative_ctx") or 16384)
                options: Dict[str, Any] = {
                    "temperature": temperature,
                    "num_ctx": proc_ctx,
                    "num_predict": max_tokens or 2048
                }
                payload = {
                    "model": active_model,
                    "prompt": prompt,
                    "think": False,
                    "stream": False,
                    "options": options
                }
                if is_json:
                    payload["format"] = "json"

                try:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    resp_data = resp.json()
                    raw = resp_data.get("response") or resp_data.get("thinking") or ""
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
