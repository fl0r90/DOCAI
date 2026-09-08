import os
import json
import re
import asyncio
from typing import Optional, Dict, Any, Union
from .llm_client import UnifiedLLMClient

class LLMService:
    """Serviciu asincron pentru interacțiunea cu motorul LLM activ (Ollama, vLLM, LM Studio)."""
    
    def __init__(self, timeout: int = 300):
        self.timeout = timeout

    async def close(self):
        pass

    async def generate(self, prompt: str, model: str, is_json: bool = False, provider: str = "") -> Union[str, Dict[str, Any]]:
        """Interfață asincronă pentru generare text/JSON via UnifiedLLMClient."""
        return await UnifiedLLMClient.async_generate(prompt=prompt, model=model, is_json=is_json, timeout=self.timeout)
