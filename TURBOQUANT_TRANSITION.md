# Decizie Arhitecturală: Tranziția la TurboQuant+
**Data:** 8 Aprilie 2026
**Autor:** Gemini CLI (Realist & Direct)

### Problema
vLLM este prea gurmand cu VRAM-ul și blochează tot sistemul în regim offline. 
Utilizarea `requests` sincrone în `grinder.py` îngheață worker-ul în timpul inferenței.

### Soluția: TurboQuant+ (TheTom/turboquant_plus)
- **Compresie KV Cache:** Am setat K=8 (q8_0) pentru precizie și V=4 (turbo4/PolarQuant) pentru densitate maximă de context (32k+ tokens pe hardware limitat).
- **Asincronism:** Refactorizare completă în `grinder.py` folosind `httpx.AsyncClient`. 
- **LLMService:** Implementat un wrapper care știe să vorbească asincron cu noul `turbo_server.py`.

### Status
- [x] Server Wrapper (turbo_server.py)
- [x] Client Async (llm_service.py)
- [x] Ingestie Async (grinder.py)
- [x] Worker Adaptat (tasks.py cu asyncio.run)
