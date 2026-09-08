# Arhitectură Tehnică - Forensic DocAI v0.7.0 BETA

## 1. Infrastructură și Servicii (Regim Offline & Air-Gapped)
- **Database:** PostgreSQL cu extensia `pgvector` pentru stocare vectorială și indexare GIN pentru Full Text Search.
- **Relații:** Neo4j pentru maparea ierarhică (Harta Documentului) și a entităților tranzacționale.
- **Cache/Queue:** Redis pentru progresul procesării, stocarea buffer-ului de rezultate și semnale de control (Stop Generation).
- **LLM Engine:** 
    - **Ollama (Principal):** Qwen 3.6-35B-A3B (MoE - Agentic Excellence, top-tier coding & document understanding), gemma4:26b (MoE - Reasoning Stability), gemma4:e4b (Balanced).
    - **Model Embedding:** bge-m3:latest (Multilingual, Dense/Sparse Hybrid Search) via Ollama sau SentenceTransformers pe CPU (0 VRAM).
- **Offline Sideloading:** Modelele sunt încărcate manual din `./models/hf_local`, fără nicio dependență de internet.

## 2. Implementări Strategice (v0.7.0 - Septembrie 2026)

### Etapa 13: Gândire Strategică și Rigoare Analitică - IMPLEMENTAT
- **Planning Phase Isolation:** Agentul este forțat să genereze un `[STRATEGIC PLAN]` în faza 1, fără acces la unelte, pentru a izola raționamentul de execuție.
- **Extended Investigation Loop:** Mărirea limitei la 15 pași cu mecanism de **Early Stop** (oprire automată când dovezile sunt suficiente).
- **Forensic Intelligence Rules:** Integrarea regulilor de **Mathematical Cross-Check** (Contract vs Factură vs Plată) și **Management Overlap** (detectare auto-tranzacționare via ONRC).
- **Evidence Confidence Layer:** Evaluarea obligatorie a nivelului de încredere (LOW/MEDIUM/HIGH) bazată pe consistența probelor coroborate.

### Etapa 14: Optimizarea Retrieval-ului și UI Forensic - IMPLEMENTAT
- **Keyword Reranking & Filename Boosting:** Algoritm de scoring care acordă prioritate de până la 50x documentelor unde entitățile căutate apar în nume sau conținut exact (eliminare zgomot din rapoarte mari).
- **TIMELINE Tool:** Unealtă nouă pentru reconstrucția cronologică a evenimentelor și tranzacțiilor unui subiect.
- **Visual Forensic Reporting:** Parsare vizuală în interfață pentru secțiunile `[FACTS]`, `[ANALYSIS]`, `[CONCLUSION]`, `[MISSING EVIDENCE]` și Badge-uri de `[CONFIDENCE]`.
- **Enhanced Citation Mapping:** Injecția automată a numelui fișierului în metadatele de căutare pentru deschiderea precisă a documentului sursă la click.

### Etapa 15: Database & Context Integrity - IMPLEMENTAT
- **Log Isolation:** Separarea logurilor de investigație (coloana `sql`) de conținutul principal al mesajului pentru a preveni poluarea contextului LLM.
- **Context Urgency:** Semnalizarea automată a limitei de pași către model pentru a forța sinteza finală în cazuri de volum mare de date.

## 3. Mandatul Agnosticismului (Regulă Absolută)
- **Agnosticism Total:** Zero referințe la conținut specific (nume, sume) în cod.
- **Evidence-Only Protocol:** Agentul este forțat prin prompt-ul de sistem să ruleze unelte de căutare înainte de orice afirmație.
- **Language Protocol:** Raționament intern în Engleză (precizie tehnică) / Raport final obligatoriu în Română.

### Etapa 16: Agentic DocAI & Quant Integrity - ÎN CURS (24 Mai 2026)
- **Qwen 3.6 Integration:** Migrarea către seria Qwen 3.6 pentru capabilități superioare de autonomie ("Agentic AI") și înțelegere de layout documente (DocAI).
- **Quant Integrity Protocol:** Forțarea interogărilor SQL (`SEARCH_STRUCTURED_DATA`) pentru întrebări ce vizează sume, cantități sau liste agregate, reducând riscul de eroare din sinteza fragmentată a vector search-ului.
- **Backend Stability Fix:** Corectarea erorilor de indentare în `chat_service.py` și stabilizarea loop-ului de restart al serviciilor.
- **Remediere Limitare Agregare (24 Mai 2026):** Adăugarea parametrului `limit` (implicit 30, configurabil) pentru a permite agentului să preia liste mai mari de entități fără trunchiere.
- **Optimizare Performanță RAG (Capping Limit):** Căparea parametrului `limit` la un maximum de 100 de înregistrări în codul uneltei `SEARCH_STRUCTURED_DATA` (în loc de 300) pentru a proteja instanța locală de Ollama împotriva blocajelor de VRAM paging și a timeout-urilor (eroare 500) pe GPU-uri cu 8GB VRAM la contexte mari, menținând în același timp destulă informație pentru corelări logice corecte.

### Etapa 17: Trace & Live Logs UI - IMPLEMENTAT (27 Mai 2026)
- **JSON Serialization of Agent Logs:** Modificarea backend-ului (`cases.py`) pentru a salva toate evenimentele intermediare (`status`, `step`, `tool_call`, `observation`) ca JSON array în coloana `ChatMessage.sql`.
- **Live Trace Logs Viewer:** Implementarea în interfața de chat (`page.tsx`) a unui panou pliabil unificat ("Jurnal Investigare") care prezintă în timp real și istoric logurile procesului de gândire, tool calls și rezultatele acestora (observațiile).

### Etapa 18: Arhitectură Multi-Engine & Suport LM Studio (Local / Remote) - IMPLEMENTAT (Septembrie 2026)
- **Unified LLM Client (`llm_client.py`):** Crearea unui adaptor unificat agnostic care rutează cererile către **Ollama** (`/api/chat`, `/api/generate`), **vLLM** (`/v1/chat/completions`) sau **LM Studio** (`/v1/chat/completions`).
- **Suport Ambidextru (Chat + Procesare Grinder):** Atât investigatorul forensic (`chat_service.py`), cât și procesarea de documente/extracția de tabele & entități (`grinder.py`, `llm_service.py`) folosesc motorul activ selectat.
- **Conectivitate Remote & Host Gateway:** Adăugarea `extra_hosts: ["host.docker.internal:host-gateway"]` în `docker-compose.yml` și suport complet pentru configurarea unui IP extern/remote (ex: `http://192.168.x.x:1234/v1`) cu API Key opțional și testare automată de latență (`/system/llm/test-connection`).
- **Sincronizare Automată a Experților & UI Simplificat (`dashboard/llm/page.tsx`):**
    - În modul LM Studio, modelul încărcat activ este sincronizat și alocat automat la **toți experții** (`active_model`, `specialist_tabular`, `specialist_narrative`).
    - Opțiunile redundante (alegere separată de specialiști, slidere de tokeni și ferestre de Context RAM) sunt ascunse automat din UI-ul de administrare, întrucât parametrii de context și offloading sunt deciși direct în interfața LM Studio la încărcarea modelului.
- **UI Admin LLM Config (`dashboard/llm/page.tsx`):** Selector triplu (Ollama / vLLM / LM Studio), panou dedicat pentru adresa serverului LM Studio, buton live de verificare a conexiunii, detecție a modelelor și badge informativ pentru modelul unic activ.

### Etapa 19: Forensic Intelligence v0.7.0 (Antifraudă, Custodie Criptografică, GDS Graph & Distributed Ingestion) - IMPLEMENTAT (Septembrie 2026)
- **Modul Criminalistic de Detecție a Anomaliilor Financiare (`anomaly_service.py`):**
    - *Legea lui Benford:* Analiză statistică pe prima cifră a sumelor tranzacționate, calcul MAD (Mean Absolute Deviation) și calificare conformitate (Drake & Nigrini).
    - *Smurfing & Split Invoicing:* Detecție automată a plăților fragmentate sub pragurile legale de raportare (40.000 - 49.999 RON / 4.000 - 4.999 EUR).
    - *Plăți & Facturi Duplicate:* Identificare operațiuni identice pe aceleași numere de facturi sau parteneri comerciali.
    - *Aglomerare Numere Rotunde:* Monitorizare clustering pe sume rotunde mari (indicator de înțelegeri fictive).
    - *Tranzacții în Zile Nelucrătoare:* Identificare automată a plăților operate sâmbăta și duminica.
    - *Agentic Tool Integration:* Unealtă dedicată `DETECT_FINANCIAL_ANOMALIES` integrată în bucla de raționament a investigatorului (`chat_service.py`).
- **Lanț de Custodie Criptografică & Raport de Expertiză Judiciară (SHA-256):**
    - Amprentare criptografică unică SHA-256 pentru fiecare document original uploadat, salvată în baza de date.
    - Endpoint complet de generare Raport de Expertiză Judiciară PDF (`GET /cases/{case_id}/audit-report`) incluzând antet oficial, tabelul de custodie SHA-256, matricea anomaliilor financiare, sinteza probelor și rețelele de entități.
- **Deep Citation Highlighting:**
    - Extragere și persistare a coordonatelor spațiale (bounding box: `l,t,r,b`) pentru toate elementele text și tabelele din documente (`ocr_service.py`, `tasks.py`), transmise în metadatele citatelor din chat.
- **Activare Modul GDS Graph Analytics (`dashboard/graph/page.tsx` & `/system/graph`):**
    - Hartă vizuală interactivă 2D/3D (ForceGraph2D) conectată la Neo4j și PostgreSQL.
    - Algoritmi de analiză relațională: Găsește Liderul (PageRank), Detecție Carteluri (Comunități Louvain), Traseu (Shortest Path) și Detecție Clone CUI (Node Similarity).
- **Optimizare Critică VRAM - Embeddings Hibrid/CPU (`embedding_service.py`):**
    - `EmbeddingService` permite comutarea modelului `bge-m3` pe CPU via SentenceTransformers (0 MB VRAM alocat pe GPU), lăsând toți cei 8GB VRAM liberi pentru modele LLM mari (14B/32B în LM Studio).
- **Arhitectură Ingestion Distribuită (Remote Worker Nodes):**
    - Suport multi-nod pentru workeri asincroni cu `WORKER_ID` și heartbeats în Redis, monitorizați în timp real via `GET /system/workers`.

### Etapa 20: Sistem Unificat de Autentificare & Logout Ubicuos (Admin, Master, Worker) - IMPLEMENTAT (Septembrie 2026)
- **Accesibilitate Universală Logout:** Buton dedicat de deconectare (`LogOut` icon, acțiune securizată) integrat în toate zonele platformei:
    - *Master & Worker:* În bara de navigare din dosare (`/cases`), în antetul detaliului de dosar (`/cases/[id]`) și în panoul principal de lucru (`/`).
    - *Admin:* În panoul de control (`/dashboard`), în bara laterală a configurării LLM (`/dashboard/llm`), în centrul de mentenanță (`/dashboard/updates`), în modulul de analiză relațională (`/dashboard/graph`) și în managementul utilizatorilor (`/users`).
- **Curățare Criptografică a Sesiunii:** Ștergerea completă și simultană a token-ului JWT (`token`) și a rolului de securitate (`role`) din stocarea cookies înainte de redirecționarea curată către `/login`.
- **Securizare la Nivel de Transport API (`lib/api.ts`):** Interceptor Axios pentru răspunsuri HTTP `401 Unauthorized` care invalidează automat sesiunea expirată și redirecționează utilizatorul la login fără blocaje de interfață.
- **Sincronizare Versiune UI:** Alinierea tuturor referințelor vizuale de versiune la `DocAI v0.7.0 BETA` în layout și antete.
- **Remediere Navigare & Întoarcere Dosar de Lucru (`handleBack` & State Persistence):**
    - Săgeata de sus din detaliul dosarului (`/cases/[id]`) a fost reparată pentru a apela `handleBack()` (`router.back()` cu fallback la `/`), asigurând că utilizatorul revine exact în fereastra principală de lucru (`/`) din care a apăsat „Deschide Investigația”, eliminând redirecționarea forțată către `/cases`.
    - Sigla DocAI a fost transformată în scurtătură directă către Panoul Principal (`/`).
    - În fereastra `/cases` a fost adăugat buton de navigare înapoi (`ChevronLeft`) către Panoul Principal (`/`).
    - Persistența dosarului selectat (`last_selected_case_id` în `localStorage`), astfel încât la revenirea în Panoul Principal dosarul de lucru rămâne gata selectat cu toate probele și entitățile vizibile.

## 4. Configurație Media Stack NAS (XPenology) - Mentenanță Iunie 2026
- **Download Engine:** qBittorrent (Aplicație nativă Synology).
- **Automation:** Radarr (Filme) & Sonarr (Seriale) rulate în Docker.
- **Paths & Mappings (Critic):**
    - **Local Docker Path:** `/data` (mapat la `/volume1` de pe host).
    - **Download Path (Host):** `/volume1/downloads/complete` (sau `/volume1/Download/complete`).
    - **Remote Path Mapping (Radarr/Sonarr):** `host: 192.168.0.77` | `Remote: /volume1/` | `Local: /data/`.
    - **Media Root:** `/volume1/xpenology/Download/Jellyfin/Filme` (și `Seriale`).
    - **Permisiuni:** Toate folderele de media și download au fost setate la `777` (UID: 1026/abc) pentru a permite importul între aplicația nativă și containere.


---
*Ultima actualizare: Septembrie 2026 - Adăugat Etapa 19 & Etapa 20 (Forensic Intelligence v0.7.0 & Logout Ubicuos).*

### Arhitectura Completa a Sistemului Forensic DocAI (Cum functioneaza)
Sistemul este construit pe un pipeline iterativ cu mai multi pasi (pana la 15), care impune rigoare matematica si de dovezi:
1. **Agentic Investigator Loop:** Sistemul functioneaza printr-o bucla `AgenticInvestigator` care alterneaza faze de rationament (`Thinking`) cu faze de actiune (`Tool Use`). Acest lucru previne halucinatiile deoarece modelul trebuie sa astepte observatia (datele extrase).
2. **Quant Integrity Protocol (Financial Data):** Daca query-ul implica sume (bani), cantitati, bilanturi, agentului i se blocheaza accesul la rezultatele fragmentate ale vector-search-ului. E fortat prin prompt injectat sa apeleze `SEARCH_STRUCTURED_DATA`, care randeaza aggregari din baza de date relationala (PostgreSQL).
3. **Hybrid Search cu Reranker:** Pentru text (contracte, extrase), se apeleaza `SEARCH_TEXT`. Vectorii sunt adusi din extensia `pgvector`, apoi rerankati cu `BAAI/bge-reranker-base` pentru a asigura densitatea informatiei (Cross-Encoder).
4. **Early Stop Mechanism:** Agentul nu e fortat sa ajunga la pasul 15. Imediat ce are `[FACTS]` complete care raspund integral la intrebarea utilizatorului, opreste bucla si emite o concluzie.
5. **Graph Search (Harta Documentului):** Utilizand `Neo4j`, cand agentul gaseste entitati (nume de companii), poate extrage conexiunile ierarhice (actionariat, auto-tranzactionare, management overlap).
