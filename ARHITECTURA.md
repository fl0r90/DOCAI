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
- **Ghid Autonom de Deploy (README.md):** Documentarea procedurii complete de lansare pe o mașină nouă via GitHub + LM Studio, fără transfer de arhive sau modele mari pe suport fizic.

### Etapa 21: Integritate Baze Multiple (AUTH vs FORENSIC), Endpoint Schimbare Parolă & Reziliență Rutare Dosare - IMPLEMENTAT (Septembrie 2026)
- **Implementare Endpoint Schimbare Parolă (`POST /auth/change-password`):**
    - La prima logare cu conturile implicite (`admin` sau `master`), sistemul forțează schimbarea parolei (`needs_password_change = 1`).
    - A fost implementat endpoint-ul dedicat `/auth/change-password` care validează lungimea parolei, o criptează prin bcrypt, resetează flag-ul de schimbare forțată (`needs_password_change = 0`) și sincronizează modificarea în ambele baze de date (`auth_db` și `forensic_db`).
    - Adăugat endpoint `/auth/request-reset` pentru înregistrarea cererilor de recuperare cont direct în baza de date și în audit logs.
- **Sincronizare Automată a Utilizatorilor & Integritate Referențială Cross-Database:**
    - Sistemul utilizează două baze de date distincte pe PostgreSQL (`auth_db` pentru identitate și `forensic_db` pentru dosare/probe).
    - Anterior, utilizatorii erau creați doar în `auth_db`, lăsând tabelul `users` din `forensic_db` gol. La crearea unui dosar nou (`POST /cases`), constrângerea PostgreSQL `cases_created_by_fkey` eșua cu `ForeignKeyViolation (Key created_by=X is not present in table users)`, cauzând eroare 500.
    - S-a introdus mecanismul de sincronizare bidirecțională automată (`sync_users_auth_to_forensic` la pornirea backend-ului și `sync_single_user_to_forensic` la crearea/actualizarea userilor).
    - Au fost eliminate constrângerile rigide cross-database la nivel de DB (`cases_created_by_fkey`, `case_members_user_id_fkey`, `case_members_added_by_fkey`, `audit_logs_user_id_fkey`), garantând că operațiunile pe dosare nu sunt blocate chiar dacă bazele de date sunt exportate sau restaurate independent.
- **Reziliență Rutare API (Trailing Slash & CORS):**
    - Rutarea pentru dosare acceptă acum ambele variante fără redirecționare 307: `@router.get("")`/`@router.get("/")` și `@router.post("")`/`@router.post("/")`, prevenind pierderea header-ului `Authorization: Bearer` la cererile clientului Axios din frontend.
    - Asigurată igienizarea automată a numelui dosarului (`trim` + fallback la "Dosar nou") și sincronizarea opțională a nodului `Case` în graful Neo4j.
- **Prevenire Blocaj la Ștergerea Dosarelor (`AuditLog FK Decoupling`):**
    - La ștergerea unui dosar (`POST /cases/{id}/delete`), logurile de audit legate de dosar sunt decuplate automat (`case_id = NULL`), prevenind violarea constrângerii `audit_logs_case_id_fkey` și permițând ștergerea completă a dosarului și a probelor sale.
- **Corecție Tip Dată `User.is_active`:**
    - Aliniat modelul SQLAlchemy `is_active` ca `Integer` (implicit 1) conform schemei reale a tabelului PostgreSQL, prevenind eroarea `DatatypeMismatch (column is_active is of type integer but expression is of type boolean)`.

## 4. Configurație Media Stack NAS (XPenology) - Mentenanță Iunie 2026
- **Download Engine:** qBittorrent (Aplicație nativă Synology).
- **Automation:** Radarr (Filme) & Sonarr (Seriale) rulate în Docker.
- **Paths & Mappings (Critic):**
    - **Local Docker Path:** `/data` (mapat la `/volume1` de pe host).
    - **Download Path (Host):** `/volume1/downloads/complete` (sau `/volume1/Download/complete`).
    - **Remote Path Mapping (Radarr/Sonarr):** `host: 192.168.0.77` | `Remote: /volume1/` | `Local: /data/`.
    - **Media Root:** `/volume1/xpenology/Download/Jellyfin/Filme` (și `Seriale`).
    - **Permisiuni:** Toate folderele de media și download au fost setate la `777` (UID: 1026/abc) pentru a permite importul între aplicația nativă și containere.


### Etapa 22: Decuplare Asistent Chat în Fundal (Persistență la "Back"), Căutare Temporală Multiformat & Prevenire Concluzii Negative Premature - IMPLEMENTAT (Septembrie 2026)
- **Decuplare Rulare Investigație în Fundal & Rezistență la Navigare ("Back" Persistence):**
    - Anterior, generatorul SSE din endpoint-ul `/cases/{case_id}/chat` rula sincron în corpul funcției `stream()`. Dacă utilizatorul naviga înapoi (`router.back()`) sau închidea tab-ul în timpul investigației, conexiunea HTTP era întreruptă, FastAPI arunca `GeneratorExit`, iar codul de salvare a mesajului asistentului din baza de date nu era niciodată executat.
    - S-a decuplat executarea agentului într-un worker thread dedicat (`threading.Thread(target=run_investigation, daemon=True)`) comunicând cu generatorul HTTP prin `queue.Queue`.
    - Chiar dacă utilizatorul dă "Back", worker-ul continuă investigația în fundal și salvează garantat răspunsul (`role='assistant'`) în tabelul `chat_messages` din `forensic_db`. La următoarea accesare a dosarului, răspunsul este gata persistat.
- **Normalizare & Detecție Multiformat de Date Temporale (`get_date_variants`):**
    - Adăugată extragerea și generarea automată a tuturor formatelor de date (ex: `17.01.2025`, `17-01-2025`, `17/01/2025`, `17 ianuarie 2025`, `2025-01-17`).
    - În `tool_search_text`, fragmentele care conțin variațiile de dată sunt interogate direct prin `ILIKE` și primesc boost de relevanță în Cross-Encoder Reranker și în scorul de fallback, eliminând ratarea chunk-urilor cauzată de diferențele de punctuație (puncte vs cratime).
    - În `tool_search_transactions` (atât pe modul `aggregate`, cât și pe fallback), filtrele de căutare potrivesc acum data pe antetul de context al chunk-ului (`Context: ... Data: 17-01-2025`), permițând parsarea automată a tabelelor de prezență unde data este în antetul fișierului și nu pe fiecare rând de tabel.
- **Prevenire Concluzii Negative Premature ("Anti-Hallucinated Negative Guard"):**
    - Rezolvată cauza eșecului din mesajul 818, unde agentul apela doar `SEARCH_STRUCTURED_DATA` (care căuta în tranzacții financiare), obținea 0 rânduri și concluziona eronat cu `[CONFIDENCE]: HIGH` că nu există probe, fără a căuta în textul documentelor.
    - S-a implementat un gardian de integritate în bucla agentului: dacă modelul încearcă să emită un `[FINAL RESPONSE]` cu formulare negativă ("nu există dovezi", "nu s-au găsit"), dar nu a apelat niciodată `SEARCH_TEXT`, concluzia este respinsă automat, iar agentul primește instrucțiunea explicită de a rula `SEARCH_TEXT` înainte de a putea finaliza.
- **Eliminare Duplicare Întrebare în Istoric (`_load_history`):**
    - S-a introdus deduplicarea automată în `_load_history` pentru a evita apariția dublă a întrebării utilizatorului în contextul LLM (cauzată de salvarea mesajului utilizator în DB chiar înainte de lansarea agentului).

### Etapa 23: Upgrade Reranker (BAAI/bge-reranker-v2-m3) & Chunker Semantic Structurat (Markdown, Tabele & Parent-Child) - IMPLEMENTAT (Septembrie 2026)
- **Upgrade Reranker la `BAAI/bge-reranker-v2-m3`:**
    - Înlocuit modelul vechi `BAAI/bge-reranker-base` (care era centrat pe engleză/chineză) cu modelul multilingv de generație nouă `BAAI/bge-reranker-v2-m3`.
    - Reranker-ul rulează forțat pe CPU (`device='cpu'`) în containerul `v2-backend`, lăsând VRAM-ul dedicat 100% instanței LLM. Rularea pe CPU durează sub 1 secundă pentru zeci de candidați.
    - Oferă o granularitate excepțională pentru limba română (pe query-uri de control pe registre de cursuri și facturi a atins scoruri calibrate de relevanță de ~0.94 pentru chunk-ul relevant vs ~0.000016 pentru chunk-uri irelevante).
    - Suportă configurare flexibilă prin variabila de mediu `RERANKER_MODEL`.
- **Implementare `SemanticChunker` (`backend/core_engine/services/chunker_service.py`):**
    - S-a eliminat decuparea mecanică la 350 de caractere care secționa cuvinte, numere, CNP-uri și fragmenta tabelele în linii orfane.
    - Noul modul `SemanticChunker` analizează ierarhia Markdown (`#`, `##`, `###`), paragrafele și tabelele.
    - **Păstrare Tabele:** Tabelele Markdown până în 2500 de caractere sunt păstrate 100% intacte într-un singur chunk. Blocurile consecutive de tabel despărțite de linii goale la conversia Docling sunt unite automat.
    - **Tabele Mari:** Pentru tabele extinse (> 2500 caractere), tăierea se face exclusiv între rânduri întregi, iar primele 2 rânduri de antet ale tabelului sunt replicate automat pe fiecare slice rezultat pentru a păstra semnificația coloanelor.
    - **Breadcrumbs Contextuale:** Fiecare chunk primește automat antetul de context: `[Doc: <nume_fișier> | <Cale Header>]`.
    - **Hierarchical Parent-Child Retrieval:** Generează bucăți `Parent Chunk` (context larg până la 4500 caractere pentru sinteza LLM) și bucăți `Child Chunk` (cu embedding calculat prin `BAAI/bge-m3` pentru căutare spectrală în `pgvector`).
- **Păstrarea Embedder-ului `BAAI/bge-m3`:**
    - Modelul `BAAI/bge-m3` (1024 dimensiuni, suport nativ de până la 8192 tokeni context) a fost păstrat deoarece este deja calibrat pe schema tabelelor `document_chunks` și `document_storage` din PostgreSQL (`vector(1024)`).
- **Corecții Pipeline OCR & Ingestion (`ocr_service.py` & `tasks.py`):**
    - Tabelele extrase de Docling sunt adăugate acum garantat atât în `items`, cât și în `chunks`, asigurând că nicio informație tabulară nu se pierde la indexare.
    - Funcția `_create_chunks_and_embeddings` din `tasks.py` acceptă `raw_markdown` și apelează `SemanticChunker`, salvând ierarhia `parent_chunk_id` în `document_chunks` și `document_storage`.
- **Re-indexare DB:** Toate cele 62 de documente existente în baza de date au fost re-procesate și re-vectorizate cu noul sistem semantic.

### Etapa 24: Schemă Deschisă Dinamică (Open-World Key-Value Schema) & Document Diversity Retrieval - IMPLEMENTAT (Septembrie 2026)
- **Extracție Dinamică de Atribute (Open-World Key-Value Extraction):**
    - S-a eliminat restricția schemelor rigide SQL unde documentele erau forțate exclusiv în coloane predefinite (ex: tranzacții financiare).
    - În faza de Grinder (`backend/core_engine/services/grinder.py`), LLM-ul analizează macro-contextul documentului și extrage liber dicționarul deschis `dynamic_attributes` / `atribute_specifice` (ex: pentru cursuri: `disciplina`, `instructor`, `numar_participanti`; pentru facturi: `seria_factura`, `scadenta_plata`, `iban_plata`; pentru contracte: `obiect_contract`, `locatie`, etc.).
    - Extracția macro identifică și populează automat coloanele de prim rang ale documentului: `doc_type`, `doc_number`, `doc_date` și `ai_summary`.
- **PostgreSQL JSONB & Index GIN (`forensic_db`):**
    - Atributele dinamice sunt persistate în câmpul `doc_metadata` al fiecărui document.
    - S-a adăugat indexul binar GIN: `CREATE INDEX idx_documents_doc_metadata_gin ON documents USING gin ((doc_metadata::jsonb))`. Căutările în proprietățile arbitrare ale documentelor rulează în sub 2ms.
    - S-a adăugat coloana `created_at` în tabelul `document_entity_links` pentru a asigura sincronizarea completă SQLAlchemy.
- **Proprietăți Dinamice Schemaless în Neo4j (`graph_service.py`):**
    - Toate atributele dinamice extrase (șiruri, numere, date) sunt setate direct ca proprietăți dinamice pe nodul `(:Document {id: ...})` în Neo4j (`SET d += $props`), alături de `doc_type`, `doc_date` și `doc_number`.
- **Document Diversity Retrieval (`chat_service.py`):**
    - Rezolvată limitarea `[:10]` din `tool_search_text` care tăia documentele când o căutare viza zeci sau sute de fișiere (ex: cele 17 cursuri ale unui instructor).
    - Noul algoritm grupează rezultatele după `document_id` și selectează cele mai bune fragmente distribuite echilibrat pe până la 25-30 de documente distincte.
    - Căutarea după `semantic_intent` a fost extinsă pentru a căuta atât în `doc_type` și `filename`, cât și în toate cheile și valorile din `dynamic_attributes`.
    - Citațiile returnate agentului includ automat eticheta `doc_type` pentru conștientizare contextuală imediată.

### Etapa 25: Decompunere Întrebări Atomice, Scratchpad Memory, Context 4096 & Zoom Ierarhic - IMPLEMENTAT (Septembrie 2026)
- **Decompunere Automată pe Ținte Atomice (`decompose_question`):**
    - Întrebările complexe ale utilizatorului cu multiple aspecte sau cerințe factuale (ex: hash SHA-256 + IP-uri + volum date) sunt sparte automat în componente atomice încă din faza de inițializare, eliminând diluarea atenției („attention dilution”) din LLM.
- **Memorie Temporară Structurată (Progressive Scratchpad):**
    - Agentul menține o stare dinamică a fiecărei ținte: `status` (PENDING / RESOLVED / NOT_FOUND) și `confidence` (NONE / LOW / MEDIUM / HIGH), asociate cu faptele verificate și citările `[REF x]`.
    - Probele confirmate sunt înghețate în memorie cu `Confidence: HIGH`, prevenind regresiile, contrazicerile sau re-evaluările redundante între pașii de investigație.
- **4096-Caractere Context per Document (`tool_search_text`):**
    - S-a implementat limita de 4096 caractere per document în căutarea contextuală hibridă.
    - Rezultatele candidate sunt agregate la nivel de document (`doc_matches`), păstrând ordonarea de relevanță dată de neuroranker/scor.
    - Pentru orice document sub 4096 de caractere, conținutul integral (`raw_text`) este livrat fără nicio tăiere mecanică sau pierdere de secțiuni (asigurând că amprentele criptografice SHA-256, tabelele de rețea, volumele de date și datele tehnice sunt vizibile simultan în faza 1 a investigației).
    - Pentru documentele mai mari de 4096 de caractere, sistemul decupează o fereastră de 4096 caractere centrată matematic pe fragmentul identificat.
    - Citațiile sunt unificate per document (o singură intrare de citare `[REF x]` per fișier), eliminând citările duplicate pe pagini sau bucăți redundante.
- **Zoom Ierarhic Contextual la `Confidence: MEDIUM` (`tool_fetch_full_document`):**
    - Dacă pentru o țintă se găsesc doar indicii parțiale sau ambigue (`Confidence: MEDIUM`), agentul are la dispoziție unealta dedicată `FETCH_FULL_DOCUMENT(doc_id, focus_terms)` pentru a inspecta fișierul integral sau paragrafele adiacente extinse.
- **Recompunere Finală Rapidă & Optimizare Latență:**
    - S-a eliminat constrângerea artificială de 5 pași obligatorii.
    - Când toate țintele atomice din Scratchpad ating `Confidence: HIGH` (ori certitudine de absență în dosar), agentul emite direct raportul consolidat.
    - Contextul `num_ctx` a fost aliniat dinamic cu parametrul `chat_ctx` din configurația de motor (16.384 tokeni), eliminând alocarea redundantă de 32k pe CPU/RAM.
- **Epurare & Compresie Istoric Conversație (`_load_history`):**
    - S-a redus fereastra de mesaje din istoric de la 10 la 4 (2 runde complete de întrebare-răspuns).
    - Răspunsurile lungi ale asistentului din mesajele trecute sunt compresate/trunchiate la maximum 1200 de caractere pentru a preveni „bleed-through”-ul (poluarea noului context cu liste masive de persoane sau tabele din interogări anterioare).
- **Agnosticism Total Restabilit:**
    - Au fost eliminate toate exemplele de domeniu particulare („curs”, „training”, „prezență”, etc.) din prompturile preliminare, descrierile uneltelor (`SEARCH_TEXT`) și din mesajele de avertizare la concluzii negative fără căutare.

### Etapa 26: Motor Dinamic de Calcul ETA și Urmărire Progres Live (DocProgressTracker) - IMPLEMENTAT (Septembrie 2026)
- **Eliminarea Estimărilor Statice Hardcodate:**
    - Anterior, timpii ETA erau fixați rigid la 120s (OCR), 60s (RAG) și 300s (AI Grinder), ignorând dimensiunea documentului, iar în etapele intermediare din Grinder câmpul `eta_seconds` lipsea, forțând UI-ul în starea statică `'calculând...'`.
    - În frontend, lipsa cheilor `current_segment` și `total_segments` producea afișajul `Segment undefined / undefined`.
- **Serviciu Centralizat `DocProgressTracker` (`core_engine/services/progress_tracker.py`):**
    - *Detecție Atomică a Volumului:* Inspectare instantanee PyMuPDF (`fitz`) la start pentru calculul numărului real de pagini (`total_pages`).
    - *Ticker Asincron de Fundal (Daemon Thread):* Pe durata apelurilor blocante (Docling RapidOCR și sinteză LLM), un thread de fundal decrementează ETA secundă cu secundă în Redis (`doc_progress_{doc_id}`) și estimează pagina curentă (`pag ~X/Y`), oferind o bară de progres lină (5% -> 38%) fără înghețarea interfeței.
    - *Calibrare Adaptivă a Vitezei:* Măsurarea vitezei efective per pagină din OCR pentru re-calibrarea dinamică a etapelor aval (RAG și Grinder).
    - *Monitorizare Granulară RAG:* Urmărirea progresului chunk cu chunk în bucla de embeddings (`processed_children / total_children`), cu recalcularea mediei mobile de latență și avans procentual (40% -> 60%).
    - *Urmărire Granulară Grinder:* Descompunerea etapei de analiză forensică pe pași atomici (Sinteză macro + fiecare tabel auditat), garantând că `current_segment` și `total_segments` sunt întotdeauna numere întregi coerente.
### Etapa 27: Injectare Dinamică de Context & Eliminare Puncte Oarbe (Context-Aware Document Sizing) - IMPLEMENTAT (Septembrie 2026)
- **Eliminarea Limitei Artificiale Hardcodate de 4096 Caractere:**
    - Anterior, uneltele de căutare (`SEARCH_TEXT` și `FETCH_FULL_DOCUMENT`) decupau forțat o fereastră de maximum 4096 de caractere per document, indiferent de capacitatea reală a contextului LLM. Acest lucru ducea la pierderea contextului narativ la persoana I (ex: mențiunea numelui pe copertă și descrierea locului de muncă/activităților la câteva pagini distanță).
- **Calcul Dinamic al Bugetului Util de Text (`_get_context_budget`):**
    - Sistemul inspectează direct parametrul activ `chat_ctx` (ex: 16.384 sau 32.768 tokeni).
    - Rezervă o marjă de 3.200 tokeni pentru prompt-ul de sistem, unelte, istoricul de conversație, raționamentul interior (`<think>`) și răspunsul final.
    - Transformă tot restul ferestrei de context în capacitate utilă de caractere (~3.5 caractere / token). La 16.384 tokeni, bugetul este de **~46.000 de caractere**, permițând injectarea INTEGRALĂ (100%) a documentelor de până la 39.000 de caractere.
- **Validare & Fidelitate Factuală:**
    - Testat cu succes pe documente reale de peste 22.000 de caractere (`Puterea bibliotecii în modelarea unei societăți informate`), unde întregul text este acum injectat dintr-o singură privire în `SEARCH_TEXT`, incluzând toate capitolele, studiile de caz locale și observațiile autoarei fără nicio trunchiere.

### Etapa 28: Rolling Scratchpad Engine (Audit Progresiv Fără Limită de Context) - IMPLEMENTAT (Septembrie 2026)
- **Problemă rezolvată (Sinteză pe Documente Voluminoase):**
    - Chiar și cu mărirea ferestrei de context (Etapa 27), documentele extrem de mari (cărți, volume de sute de pagini, dosare penale masive de 200.000 - 1.000.000 de caractere) depășesc limita utilă dintr-un singur apel. RAG-ul clasic prin similitudine vectorială tinde să extragă doar cele mai dense fragmente semantice (ex: capitolele din mijloc), omițând debutul sau epilogul cărții.
- **Arhitectura Rolling Scratchpad (`run_rolling_scratchpad_digest`):**
    - *Partiționare Dinamică cu Overlap:* Documentul este împărțit în calupuri consecutive de ~32.000 de caractere cu o zonă de siguranță de 1.000 de caractere suprapunere pentru a nu rupe fraze sau idei.
    - *Acumulare Progresivă în Memoria de Lucru:* Fiecărui calup i se aplică un prompt forensic riguros care primește starea curentă a Scratchpad-ului și noul calup de text. LLM-ul păstrează dovezile anterioare, extrage probele și evoluțiile noi și actualizează memoria de lucru condensată.
    - *Acoperire 100% Garantată:* Toate paginile sunt auditate filă cu filă fără omisiuni. La final, agentul primește un distilat consolidat cu citare completă `[REF x]`.
    - *Feedback Live prin SSE:* Fiecare calup analizat emite mesaje de status în timp real în fluxul SSE (`📖 [Rolling Scratchpad X/Y]...`), permițând utilizatorului să urmărească investigația pas cu pas fără impresia că sistemul este blocat.
- **Integrare Agnostică & Unelte:**
    - Noua unealtă `ROLLING_SCRATCHPAD_AUDIT` adăugată în arsenalul agentului.
    - `FETCH_FULL_DOCUMENT` a fost extins astfel încât dacă un document depășește bugetul util de context, declanșează automat mecanismul iterativ în loc să trunchieze mecanic conținutul.
    - Pre-procesorul de query (`_pre_process_query`) recunoaște intențiile de analiză de ansamblu/evoluție și ghidează direct agentul către modul progresiv.

### Etapa 29: Motor Hibrid OCR cu 3 Viteze (3-Speed Hybrid OCR Engine) - IMPLEMENTAT (Septembrie 2026)
- **Problemă rezolvată (Optimizare masivă a ingestiei OCR):**
    - Anterior, Docling rula întotdeauna cu OCR activat (`do_ocr = True` prin RapidOCR), chiar și pe PDF-uri 100% native digitale. Aceasta ducea la timpi mari de conversie (40-60 secunde pentru cărți sau documente lungi de text nativ) și la instanțierea repetată a convertoarelor la fiecare document.
- **Arhitectura cu 3 Viteze (`ocr_service.py`):**
    - *Viteza 1 (Digital Fast-Path):* Verificare eșantionată a paginilor cu PyMuPDF (`fitz`). Dacă textul nativ depășește media de 80 caractere/pagină, Docling rulează cu `do_ocr = False` printr-un convertor singleton dedicat. Timp de conversie: **1-3 secunde** chiar și pentru sute de pagini, cu fidelitate de 100% a textului digital.
    - *Viteza 2 (Scanned PDF - Singleton RapidOCR):* Pentru PDF-uri scanate (fără strat digital), se folosește un convertor singleton Docling cu `RapidOcrOptions()` la nivel de proces, eliminând reîncărcarea modelelor ONNX între fișiere.
    - *Viteza 3 (Vision AI Fallback):* Pentru fișiere imagine pure (`.jpg`, `.jpeg`, `.png`, `.webp`) sau scanări extrem de degradate unde OCR-ul clasic extrage sub 50 de caractere, imaginea este optimizată (max 1024px JPEG) și transmisă modelului Vision (`gemma4:e4b` pe Ollama) pentru transcriere markdown fidelă, cu fallback terțiar pe Tesseract.

### Etapa 30: Persistență Stare Chat & Reziliență la Refresh/Tab Închis - IMPLEMENTAT (Septembrie 2026)
- **Problemă rezolvată (Pierderea feedback-ului vizual la F5):**
    - Când o investigație LLM complexă durează mai multe minute (ex: Rolling Scratchpad pe CPU), un refresh accidental în browser sau închiderea tab-ului distrugea conexiunea SSE locală. Utilizatorul vedea doar întrebarea fără niciun indicator de viață, deși serverul muncea la 700% CPU în fundal.
- **Sincronizare de Stare prin Redis & Polling:**
    - În `run_investigation` (`api/cases.py`), la fiecare pas sau raționament (`thought`/`step`), starea live a investigației este salvată în Redis: `chat_status_{case_id}`.
    - Adăugat endpoint rapid `GET /cases/{case_id}/chat/status`.
    - În frontend (`cases/[id]/page.tsx`), la încărcare și la fiecare 5 secunde, interfața interoghează starea din Redis. Dacă investigația este activă, afișează un card pulsing de status cu pasul curent și buton de Stop. Când investigația se finalizează, istoricul de mesaje este reîncărcat automat cu răspunsul complet persistat în Postgres.

### Etapa 31: Multi-Domain Forensic Prompt & Positional Boundary Retrieval - IMPLEMENTAT (Septembrie 2026)
- **Problemă rezolvată (Specializare pe domenii mixte & ratarea secțiunilor de graniță):**
    - În investigații reale, dosarele conțin tipuri eterogene de probe: contracte juridice, exporturi de mesagerie (WhatsApp/Telegram), extrase/facturi financiare și cărți/studii voluminoase.
    - Când întrebările vizau secțiuni structurale specifice (ex: clauze finale, epilog, semnături/anexe sau preambul/debut), căutarea semantică clasică returna uneori pasaje din mijlocul documentului, iar modelele compacte (5B) tindeau să fabuleze în loc să ceară context suplimentar. De asemenea, descompunerea întrebărilor compuse fragmenta naiv sintagmele legate prin „și”.
- **Arhitectura actualizată (`chat_service.py`):**
    - *Descompunere Precisă a Întrebărilor (`decompose_question`):* Separarea pe sub-ținte se face exclusiv când conjuncția este urmată de adverbe/pronume interogative (`și cum`, `și ce`, `și de ce`), prevenind fragmentarea eronată a sintagmelor („insultele și calomniile”).
    - *Clasificare Agnostică Multi-Domeniu (`_pre_process_query`):* Recunoaște automat intenții specifice pentru Contracte/Legal, Chat-uri WhatsApp/Cronologie, Tabele Financiare, Audit Exhaustiv și Ancore de Poziție (Final/Epilog vs Debut/Preambul).
    - *Căutare Hibridă cu Ancore Poziționale (`tool_search_text`):* Când o întrebare țintește sfârșitul sau începutul unui document, primele/ultimele calupuri sunt injectate garantat în setul de candidați înainte de reranking, prevenind omiterea epilogului sau anexelor.
    - *System Prompt Multi-Domeniu & Rigoare Criminalistică:* Instrucțiuni explicite pentru contracte (părți, clauze, răspundere), chat-uri (cronologie, expeditor/destinatar, timestamp-uri), finanțe și cărți, interzicând speculațiile și forțând raportarea la `[MISSING EVIDENCE]` când datele lipsesc.

---
*Ultima actualizare: Septembrie 2026 - Adăugat Etapa 29 (3-Speed Hybrid OCR), Etapa 30 (Chat State Persistence) și Etapa 31 (Multi-Domain Forensic Prompt & Positional Retrieval).*

### Arhitectura Completa a Sistemului Forensic DocAI (Cum functioneaza)
Sistemul este construit pe un pipeline iterativ cu mai multi pasi (pana la 15), care impune rigoare matematica si de dovezi:
1. **Agentic Investigator Loop:** Sistemul functioneaza printr-o bucla `AgenticInvestigator` care alterneaza faze de rationament (`Thinking`) cu faze de actiune (`Tool Use`). Acest lucru previne halucinatiile deoarece modelul trebuie sa astepte observatia (datele extrase).
2. **Quant Integrity Protocol (Financial Data):** Daca query-ul implica sume (bani), cantitati, bilanturi, agentului i se blocheaza accesul la rezultatele fragmentate ale vector-search-ului. E fortat prin prompt injectat sa apeleze `SEARCH_STRUCTURED_DATA`, care randeaza aggregari din baza de date relationala (PostgreSQL).
3. **Hybrid Search cu Reranker:** Pentru text (contracte, extrase), se apeleaza `SEARCH_TEXT`. Vectorii sunt adusi din extensia `pgvector` (folosind `BAAI/bge-m3`), apoi rerankati cu `BAAI/bge-reranker-v2-m3` (Cross-Encoder multilingv de înaltă rezoluție) pentru a asigura densitatea si relevanta informatiei.
4. **Early Stop Mechanism:** Agentul nu e fortat sa ajunga la pasul 15. Imediat ce are `[FACTS]` complete care raspund integral la intrebarea utilizatorului, opreste bucla si emite o concluzie.
5. **Graph Search (Harta Documentului):** Utilizand `Neo4j`, cand agentul gaseste entitati (nume de companii), poate extrage conexiunile ierarhice (actionariat, auto-tranzactionare, management overlap).

