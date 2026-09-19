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

### Etapa 32: Visual Knowledge Graph Decluttering & Master Toolbar Standardization - IMPLEMENTAT (Septembrie 2026)
- **Decluttering Graf Relații („Analiză Suveică” - `cases/[id]/page.tsx`):**
    - *Eliminare Zgomot Textual (Label Avalanche):* Etichetele text nu se mai randează global peste toate nodurile simultan. Afișarea se face selectiv și inteligent doar pe nodul activ la hover (`hoverNode`), nodul selectat prin click (`selectedNode`), vecinii săi direcți și rezultatele căutării live.
    - *Etichete lizibile cu Badge Pill:* Fiecare etichetă este trunchiată elegant (max 22 caractere) și randată pe canvas cu un fundal rotunjit semi-transparent (`ctx.roundRect`), asigurând lizibilitate fără suprapuneri chiar și peste muchii sau aglomerări dense.
    - *Fizică d3 Aerisită:* Forță de respingere mărită (`charge: -400`, `distanceMax: 800`, `link distance: 85`) cu decay stabil și auto-zoomToFit la deschidere.
    - *Relocare Buton Recentrează:* Mutat din centrul pânzei direct în bara superioară a modalului alături de controalele analitice (Lider, Cartel).
- **Uniformizare UI Toolbar Master (`cases/[id]/page.tsx` și `cases/page.tsx`):**
    - Toate elementele din bara superioară (Theme toggle, Badge-ul modelului LLM activ, butoanele Raport Audit, Harta Relații, Briefing, Dosar Nou și Ieșire) sunt aliniate strict la o înălțime de `h-9` (36px), `rounded-xl` și `gap-2.5`, eliminând discrepanțele vizuale de dimensiuni și margini arbitrare.

### Etapa 33: Anti-Surrender Forensic Guard & Compound Code Retrieval Resilience - IMPLEMENTAT (Septembrie 2026)
- **Problemă rezolvată (Capitulare prematură și rigiditate la coduri/extrase):**
    - În investigații complexe cu zeci de acte, modelele LLM compacte tindeau să capituleze prematur (în faza 2-3) declarând că lipsesc probele („nu există facturi/plăți”) dacă prima interogare SQL eșua sau dacă termenii din întrebare erau prea denși.
    - Când modelul specifica un `semantic_intent` (ex: `CONTRACT`), acesta funcționa ca un filtru dur (`doc_ids = intent_ids`), blocând accesul la facturile și extrasele bancare asociate.
    - În extrasele de cont bancar, numerele de facturi apar adesea prescurtate (ex: `fact 245` în loc de `FACT-2023-0245`), iar `SEARCH_STRUCTURED_DATA` eșua din cauza lipsei de flexibilitate pe sufixe numerice și entități juridice.
- **Arhitectura actualizată (`chat_service.py`):**
    - *Anti-Surrender Forensic Guard:* În bucla `AgenticInvestigator.run()`, dacă agentul încearcă să emită un răspuns de capitulare/dovezi lipsă înainte de faza 5 fără a fi explorat căutarea de text cu unelte, sistemul respinge oprirea și injectează o directivă criminalistică obligatorie de a căuta codul scurt și cuvintele cheie ale furnizorului/extraselor.
    - *Prioritizare Intentivă Soft în loc de Hard-Exclusion:* `semantic_intent` în `tool_search_text` nu mai aruncă restul documentelor din dosar, ci aplică un boost pe candidații relevanți menținând restul bazei deschisă pentru referințe încrucișate.
    - *Căutare Exactă pe Tokeni Compuși (`compound_res`):* Căutare dedicată pe tokeni cu cratimă/slash (`FACT-2023-0245`, `AGRO-CHIM`) direct în chunk-uri înainte de reranking.
    - *Extragere Automată a Numerelor Scurte:* `_pre_process_query` și fallback-ul `SEARCH_STRUCTURED_DATA` extrag automat sufixele numerice (`0245`, `245`) și elimină sufixele comerciale zgomotoase (`SC`, `SRL`, `SA`) pentru potrivire instantă în tabelele de extrase bancare.
    - *Sanitizarea Istoricului Multi-Turn:* Mesajele anterioare ale asistentului din istoric sunt condensate exclusiv la concluzia finală, prevenind poluarea promptului cu cearceafuri de `[FACTS]` din runde trecute.

### Etapa 34: Qwen 3.8 Multi-Model Resident Architecture & Truncate Resilience - IMPLEMENTAT (Septembrie 2026)
- **Problemă rezolvată (Model thrashing, erori 500 template renderer și limitări de context):**
    - Trecerea la un model de raționament criminalistic de înaltă precizie (Qwen 3.8-27B) a scos la iveală gâtuiri critice în containerul Docker de inferență și în manipularea contextului de tool-calling:
        1. Containerul Ollama rula o versiune învechită (0.20.2) care nu recunoștea arhitectura `qwen35` (eroare 500/404).
        2. Setarea `OLLAMA_MAX_LOADED_MODELS=1` determina evacuarea modelului Qwen (17.7 GB) la fiecare pas de căutare pentru a încărca `bge-m3` (embeddings), cauzând întârzieri de 25s per pas și risipă masivă de I/O.
        3. Fereastra `chat_ctx = 8192` declanșa algoritmul intern de trunchiere din Ollama (`prompt.go:36`), care la observații mari de unelte arunca primul mesaj non-system (întrebarea utilizatorului), declanșând eroarea fatală `no user query found in messages` din validatorul Qwen 3.8 (`qwen35.go:196`).
        4. Gărzile din `chat_service.py` conțineau referințe hardcodate la întrebarea anterioară, forțând modelul să răspundă repetat la aceeași temă.
- **Arhitectura actualizată (`chat_service.py`, `llm_client.py`, `docker-compose.yml`):**
    - *Upgrade Ollama 0.34.0 & Qwen 3.8 (27.3B):* Integrarea modelului Qwen 3.8 cu speculative decoding (`draft-mtp`), capabilități native de function-calling și lanț intern de gândire (*thinking*).
    - *Coexistență Multi-Model (`OLLAMA_MAX_LOADED_MODELS=3`):* Ambele modele (`qwen3.8:latest` și `bge-m3:latest`) rămân rezidente permanent în RAM/VRAM, eliminând complet model thrashing-ul.
    - *Extindere Context la 32K & Dezactivare Trunchiere Oarbă (`truncate: False`):* Creșterea ferestrei de chat la 32.768 tokeni și transmiterea flag-ului `"truncate": False` către Ollama, garantând integritatea absolută a întrebării utilizatorului în istoricul mesajelor.
    - *Plafonare Observații Unelte (`observation[:3500]`):* Limitarea dimensiunii fiecărui rezultat de unealtă pentru a preveni explozia memoriei de lucru.
    - *Restabilirea Agnosticismului Total:* Epurarea oricăror directive particulare, menținând doar ghidaje generice de căutare a codurilor alfanumerice și documentelor menționate de utilizator.
    - *Validare Experimentală Reușită:* Testat și certificat pe calcule matematice încrucișate complexe: Contract vs Factură vs Extras Bancar (penalități 49 zile) și Factură vs Extras Bancar vs Borderou Tichete de Cântar (deficit 61.50 tone / prejudiciu 67.650 RON).

### Etapa 35: Universal Deep Forensic Multi-Pass Audit Engine & Large Document Resilience - IMPLEMENTAT (Septembrie 2026)
- **Problemă rezolvată (Audit superficial de 22 secunde, trunchiere la 6.000 caractere și omiterea structurilor cheie):**
    - Pe documente voluminoase și complexe (ex: situații financiare de 70 pagini / 255.000 caractere, dosare de anchetă, contracte corporative mari), vechiul pipeline `grinder.py` aplica o trunchiere dură `doc_text[:6000]`, ignorând 97.7% din conținutul documentului.
    - Câmpul `financial_data` era lăsat gol `[]`, tabela relațională `financial_items` nu era populată pentru rapoarte mari, iar cuprinsul (TOC) rula fie euristic fără curățare structurală, fie era ignorat.
    - Rezultatul era o sinteză de doar 2 fraze generice, lăsând graful Neo4j și tabelele analitice fără date esențiale (indicatori bilanț, P&L, dosare DIICOT/ANI, litigii fiscale, părți afiliate).
- **Arhitectura actualizată (`deep_audit_service.py`, `tasks.py`, `grinder.py`, `cases.py`):**
    - *Motor Universal Multi-Pass (`DeepForensicAuditor`):*
        1. **Pass 1 - Macro & Guvernanță:** Identificare agnostică emitent, acționariat, conducere, perioadă de raportare, standard contabil (IFRS/OMFP), număr și dată oficială.
        2. **Pass 2 - Extracție Financiară & Tranzacțională:** Detectează tabelele P&L (Rezultat Global), Bilanț (Poziție Financiară) sau extrase/facturi. Parsează indicatorii pe ani comparativi (2012, 2011, 2010), normalizând valorile direct în PostgreSQL (`financial_items`) și în `doc_metadata['financial_data']`.
        3. **Pass 3 - Audit Criminalistic de Riscuri & Litigii:** Căutare dedicată pe note explicative (DIICOT, ANI, litigii civile, discounturi suspecte de gaze, investigații privind foști directori, provizioane de mediu/sonde de 175 mil. RON, risc fiscal pe 5 ani cu penalități 0.1%/zi). Toate sunt salvate în `doc_metadata['dynamic_attributes']`.
        4. **Pass 4 - Rezoluție Master Entities:** Extrage și leagă entitățile recunoscute (societăți emitente, auditori independenți precum Deloitte, autorități precum DIICOT/ANI/ANRE/ANAF, societăți asociate) în `master_entities` și `document_entity_links`.
        5. **Pass 5 - Cuprins Criminalistic Ierarhizat (TOC):** Arbore structural complet salvat în `doc_metadata['toc']` și `doc_metadata['outline']`.
        6. **Pass 6 - Raport Executiv Dens:** Generarea unui raport criminalistic structurat pe 6 capitole în `ai_summary` (7.000+ caractere de dovezi și analize factuale).
        7. **Pass 7 - Sincronizare Neo4j:** Actualizarea nodurilor `Document`, `Entity` și a relațiilor `(:Document)-[:MENTIONS]->(:Entity)` și relațiilor corporative/de anchetă.
    - *Setat ca Motor Implicit (BY DEFAULT):*
        - `tasks.py`: Pasul 5 apelează direct `DeepForensicAuditor(doc_id).run_audit()`. Orice document nou încărcat sau reîncercat trece automat prin auditul complet multi-pass.
        - `grinder.py`: Deleagă la `DeepForensicAuditor` dacă este furnizat `doc_id`.
        - `cases.py`: Expus endpoint dedicat `POST /cases/documents/{doc_id}/audit_only` pentru declanșarea exclusivă a auditului AI în fundal pe documente existente, fără reluarea OCR-ului sau re-indexare vectorială.

### Etapa 41: Granular Forensic Ledger Ingestion, Goal-Conditioned Working State & Surgical Reranker Zoom - IMPLEMENTAT (Septembrie 2026)
- **Problemă rezolvată (Gâtuirea Rolling Scratchpad și ineficiența căutărilor pe documente mari):**
    - Vechiul motor `run_rolling_scratchpad_digest` suferea de un efect de bulgăre de zăpadă: la fiecare calup nou, forța LLM-ul să rescrie integral întregul scratchpad acumulat din calupurile anterioare. Aceasta ducea la:
        1. Încetinire exponențială (de la câteva secunde la peste 1-2 minute per calup din cauza miilor de tokeni de output generați repetat).
        2. Pierderea dovezilor (*catastrophic forgetting*) prin re-comprimare continuă.
        3. Un bug critic de crash `NameError: name 'focus_terms' is not defined` la documente care se încadrau în limita de context.
    - În plus, pentru întrebări punctuale (clauze contractuale specifice, notificări, sume, semnatari), declanșarea automată a scanării oarbe pe tot documentul era un consum inutil de resurse.
- **Arhitectura actualizată (`deep_audit_service.py`, `chat_service.py`):**
    - *1. Audit Granular la Ingestie (`_audit_granular_chunk_ledger`):*
        - La procesarea documentului, textul brut este partiționat dinamic în funcție de `processing_ctx` (calibrat automat pentru RTX 5000 Ada la 32K/64K sau laptop la 16K: `chunk_chars = (processing_ctx - 4500) * 3.5`).
        - Pentru fiecare calup, se generează un micro-dosar dens (~1.500 - 2.500 caractere) structurat agnostică pe 6 axe criminalistice: Subiect/Ancoră, Părți & Entități, Clauze Legale & Obligații, Financiar & Cifre Exacte, Cronologie & Evenimente, Riscuri/Anomalii.
        - Salvat structurat în PostgreSQL în `doc_metadata['forensic_ledger']` și `doc_metadata['forensic_ledger_summary']`.
    - *2. Arhitectură de Căutare Ierarhizată (Hierarchical Retrieval):*
        - **Treapta 1 (Fast-Path / Pre-Scratchpad Ledger Hit):** În `_pre_process_query`, sistemul scanează direct dosarul granular din metadate. Dacă probele sunt complete, utilizatorul primește răspuns instantaneu (sub 2 secunde). Expusă și unealta dedicată `INSPECT_FORENSIC_LEDGER`.
        - **Treapta 2 (Surgical Reranker Zoom):** Dacă auditul identifică secțiunea/capitolul (ex: Paginile 18-24), dar este necesar textul cuvânt cu cuvânt sau formula de calcul, unealta `SEARCH_TEXT` suportă acum parametrii `doc_id`, `page_start` și `page_end`. Reranker-ul `bge-reranker-v2-m3` este aplicat strict pe candidații din acele pagini, garantând precizie chirurgicală fără zgomot.
        - **Treapta 3 (Rolling Scratchpad cu Goal-Conditioned Working State):**
            - *Context Curat & Append-Only:* LLM-ul nu mai rescrie notițele din urmă. Primește doar starea compactă de anchetă (`CE AM GĂSIT PÂNĂ ACUM` vs `CE MAI CĂUTĂM ÎN ACEST FRAGMENT`) și fragmentul curent.
            - *Accumulated Findings Ledger:* Dovezile noi (`[NOI_PROBE_IDENTIFICATE]`) sunt colectate într-o listă Python în memorie/Redis, fără context bloat.
            - *Early Stopping:* Când starea devine `COMPLET` (toate componentele întrebării au fost confirmate) și întrebarea nu solicită analiză transversală pe toate capitolele, investigația se finalizează rapid fără parcurgerea redundantă a restului de zeci de pagini.

### Etapa 42: Context-Isolated Multi-Target Engine, Dynamic Rolling Compaction & Native Thinking Capture - IMPLEMENTAT (Septembrie 2026)
- **Problemă rezolvată (Sufocarea contextului la întrebări compuse & halucinații din cauza pierderii tokenilor de raționament):**
    1. *Context Overflow (8.578 tokeni vs 8.192 n_ctx):* În întrebările multi-criteriale (ex: corelarea avizelor formale cu facturi, borderouri de cântar și chaturi WhatsApp), acumularea iterativă a 12 mesaje cu fragmente mari de text depășea limita fizică a contextului Ollama, generând HTTP 400 (`request exceeds available context size`).
    2. *Bug-ul de Pierdere a Tokenilor de Raționament (`thinking` în Qwen 3.5 / DeepSeek R1):* În streaming-ul nativ Ollama (`/api/chat`), modelele de tip reasoning emit monologul intern în câmpul `msg["thinking"]`, iar `msg["content"]` rămânea gol. Extractorul returna șir vid (`tokens_out_est: 0`), golind memoria temporară (`working_memory`) și forțând LLM-ul să inventeze din burtă cifre rotunde și povești ireale la sinteza finală.
    3. *Randare invizibilă în UI:* Regex-ul de parsare din frontend nu accepta titluri markdown (`### [FACTS]`), returnând un container gol în interfață.
- **Arhitectura actualizată (`chat_service.py`, `llm_client.py`, `frontend/src/app/cases/[id]/page.tsx`):**
    - *1. Context-Isolated Multi-Target Engine (Plan-and-Solve cu Context Flush):*
        - La Pasul 0, întrebarea este descompusă agnostică în 1–4 ținte atomice de verificare cu identificatori și chei specifice.
        - Fiecare țintă este investigată și rezolvată secvențial într-un context izolat (<2.500 tokeni), extragând faptele concrete și citările directe.
        - Faptele verificate sunt salvate în `self.working_memory`, iar balastul de text brut este eliminat complet din memorie înainte de trecerea la următoarea țintă.
    - *2. Dynamic Rolling Context Compaction (OpenCode Style):*
        - Limită flexibilă și dinamică calibrată automat în funcție de `processing_ctx` (8K pe laptop, 32K/64K pe server).
        - Prag de activare automat la 75% din capacitatea configurată (`self.compaction_threshold_tokens`).
        - La depășirea pragului, se declanșează compactarea criminalistică prin `_compact_evidence_if_needed`: modelul condensează datele într-un micro-dosar factual de mare densitate, păstrând obligatoriu toate cantitățile, seriile, sumele, TVA-ul, citatele cuvânt cu cuvânt și referințele `[REF x]`, eliminând zgomotul notarial și liniile redundante.
    - *3. Native Thinking Capture & Reasoning Fallback (`llm_client.py`):*
        - Adaptorul nativ Ollama acumulează atât `acc_content`, cât și `acc_thinking`.
        - Dacă `content` este gol dar modelul a generat în `thinking`, conținutul este extras automat din reasoning, garantând că nicio dovadă extrasă nu se mai pierde.
    - *4. UI Forensic Markdown Resilience & Safety Fallback (`page.tsx`):*
        - Regex permisiv pentru secțiunile `[FACTS]`, `[ANALYSIS]`, `[CONCLUSION]`, `[MISSING EVIDENCE]`, suportând `#`, `##`, `###`, `**` sau text simplu.
        - Afișarea antetului de dosar (`INTRO`) și fallback automat la conținut complet cu citări dacă structura nu conține tag-urile standard.
    - *5. Reranker pe CPU:*
        - `BAAI/bge-reranker-v2-m3` rulează pe CPU pentru a elibera integral cei 8GB VRAM pentru inferența LLM pe GPU.

### Etapa 43: Speculative Search Engine & Background Cross-Encoder Reranking - IMPLEMENTAT (Septembrie 2026)
- **Problemă rezolvată (Gâtuirea căutării secvențiale pe CPU & GPU Idle Wait):**
    - Reranker-ul `BAAI/bge-reranker-v2-m3` rulează pe CPU pentru a păstra cei 8GB VRAM curați pentru inferența Ollama (Qwen 3.5). Fiecare căutare hibridă durează ~35–60s pe CPU pentru filtrarea a 50–150 candidați.
    - Într-o investigație multi-target cu 3–4 obiective, executarea secvențială (Căutare 1 -> LLM 1 -> Căutare 2 -> LLM 2 -> Căutare 3 -> LLM 3) irosea peste 150–200s, deoarece GPU-ul aștepta CPU-ul, iar CPU-ul aștepta GPU-ul.
- **Arhitectura actualizată (`backend/core_engine/services/chat_service.py`):**
    - *1. Suprapunere Paralelă CPU / GPU (Speculative Prefetch):*
        - Imediat după aprobarea planului de investigație la Pasul 0, este lansat în fundal `_launch_speculative_prefetch(plan)` pe un thread daemon (`SpeculativePrefetchWorker`).
        - În timp ce Ținta 1 efectuează raționamentul pe GPU (60–90 secunde în Ollama), CPU-ul pre-calculează deja căutările hibride și rerankarea neurală pentru Țintele 2 și 3.
    - *2. Instant Cache HIT (0 ms):*
        - Când Țintele 2 și 3 își încep execuția pe thread-ul principal, dovezile rerankate sunt deja disponibile în `self.evidence_cache`.
        - Timpul de căutare pentru obiectivele ulterioare scade de la 45–60 secunde la 0 ms (economisind peste 2 minute per interogare complexă).
    - *3. Sincronizare Thread-Safe Fără Deadlock (`search_lock`, `cache_lock` & `prefetch_events`):*
        - `search_lock`: serializează execuțiile pe CPU pentru a preveni saturarea nucleelor sau conflictele de memorie în PyTorch CrossEncoder.
        - `prefetch_events`: dicționar de `threading.Event()` per cheie canonică de căutare. Dacă o țintă ajunge la pasul de interogare înainte ca worker-ul de fundal să termine, aceasta așteaptă non-blocant finalizarea worker-ului, preluând direct rezultatul din cache fără interogări duplicate.
        - `self.citations` este sincronizat sub `cache_lock`, păstrând strict indexarea coerentă a referințelor criminalistice `[REF x]`.

### Etapa 44: Hierarchical 2-Stage Reranking (Macro-Audit Reranking ➔ Micro-Chunk Zoom ➔ Rolling Scratchpad Fallback) - IMPLEMENTAT (Septembrie 2026)
- **Problemă rezolvată (Căutare 'oarbă' prin mii de chunk-uri & zgomot în dosare complexe):**
    - Când dosarele conțin zeci sau sute de documente, o căutare semantică directă pe mii de fragmente/chunk-uri (`SEARCH_TEXT`) riscă să aducă pasaje din documente irelevante care au cuvinte cheie comune (ex: clauze standard din contracte neafiliate).
    - În documentele foarte lungi, dacă chunk-urile nu conțin exact cuvintele căutate, agentul pierdea proba esențială.
- **Arhitectura actualizată (`backend/core_engine/services/chat_service.py`):**
    - *1. Stage 1: Macro-Audit Reranking (Filtrare la nivel de dosar de document):*
        - La nivel de caz, se construiește reprezentarea compactă a fiecărui document (`filename + doc_type + ai_summary + dynamic_attributes`).
        - Înainte de căutarea granulară pe chunk-uri, interogarea trece prin `_rank_relevant_documents` (CrossEncoder pe CPU, ~1s), identificând top 3-4 documente direct vizate (`target_doc_ids`).
        - Căutările pe text sunt restricționate strict în cadrul documentelor selectate la nivel macro, eliminând 95% din zgomot. Dacă nu se găsește niciun rezultat, sistemul face fallback automat la întregul dosar.
    - *2. Stage 2: Micro-Chunk Zoom & Speculative Cache:*
        - Paginile și paragrafele documentelor țintă sunt rerankate neural la nivel de micro-chunk.
        - Worker-ul speculativ de prefetch rulează în fundal pe CPU în timp ce LLM-ul gândește pe GPU, producând cache hit-uri instantanee (0 ms) pentru toate țintele ulterioare.
    - *3. Stage 3: Rolling Scratchpad Fallback:*
        - Dacă căutarea textuală nu returnează niciun fragment relevant, sistemul nu capitulează: apelează `tool_fetch_full_document(best_doc_id)` și parcurge documentul complet pagină cu pagină conform protocolului Rolling Scratchpad.
    - *4. Optimizare Volum Chunk-uri (Deduplicare & Capping):*
        - Limitarea și deduplicarea fragmentelor per sub-target la top 6 chunk-uri unice pentru a menține volumul de dovezi sub 8.000 caractere (~2.000 tokeni), prevenind compactarea distructivă și blocajele de sampler în `llama-server`.
    - *5. Agnostic Working Memory Clue Propagation (Inter-Target Chaining):*
        - Rezolvă problema investigațiilor oarbe în etape secvențiale: când o țintă anterioară descoperă entități sau coduri necunoscute la Pasul 0 (ex: mențiuni de firme partenere, coduri de facturi/contracte, sume specifice), metoda `_extract_clues_from_working_memory` le identifică 100% agnostic (folosind regex structural + potrivire cu nodurile `MasterEntity` ale dosarului).
        - Clues-urile ne-căutate sunt injectate dinamic în cheile de căutare ale sub-targeturilor următoare, permițând Cross-Encoder-ului să găsească automat documentele adiacente fără ca utilizatorul să trebuiască să le numească explicit în întrebarea inițială.


### Etapa 45: 2-Stage Asynchronous Ingestion Pipeline (CPU Extractor || GPU Auditor Concurrency) - IMPLEMENTAT (Septembrie 2026)
- **Problemă rezolvată (VRAM Thrashing & Timpi morți la procesarea calupurilor de documente):**
    - În versiunile anterioare, worker-ul procesa documentele strict secvențial: descărca LLM-ul din GPU VRAM (`_unload_ollama()`), rula Docling OCR și vectorizarea pe CPU, apoi reîncărca LLM-ul în VRAM pentru Deep Forensic Audit.
    - Când se încărcau mai multe documente, CPU-ul stătea blocat în idle 40–60 de secunde cât timp LLM-ul audita pe GPU documentul curent, iar la fiecare document nou se pierdeau 10–15 secunde reîncărcând modelul în VRAM.
- **Arhitectura actualizată (`backend/worker/tasks.py`):**
    - *1. Decuplare Totală Hardware (CPU vs GPU):*
        - S-a constatat că Docling OCR și `BAAI/bge-m3` (embeddings) rulează 100% pe CPU și consumă 0 MB VRAM. Nu există nicio coliziune de memorie cu Ollama.
        - `_unload_ollama()` a fost eliminat, permițând modelului de audit (`granite4.2:8b`) să rămână cald în VRAM permanent.
    - *2. Stage 1: CPU Ingestion Worker (`_cpu_ingestion_loop`):*
        - Preia documentele din starea `QUEUED`, efectuează Docling OCR și indexarea semantică a chunk-urilor în `pgvector` pe CPU.
        - La finalizare, marchează documentul ca `AI_PENDING` (vizibil în UI ca „În Coadă AI”).
    - *3. Stage 2: GPU Forensic Auditor (`_gpu_audit_loop`):*
        - Preia documentele `AI_PENDING`, ține modelul LLM încărcat și execută `DeepForensicAuditor` (cele 8 etape criminalistice).
        - Rulează complet concurent: în timp ce GPU-ul auditează Documentul 1, CPU-ul termină deja OCR-ul și vectorizarea pentru Documentele 2 și 3.
        - Timpul mort dintre documente scade la **0 ms**.

### Etapa 46: Dynamic Neural Reranker Control & Hardware Target Switching (Admin UI + Hot-Reload) - IMPLEMENTAT (Septembrie 2026)
- **Problemă rezolvată:**
    - Reranker-ul neuronal Cross-Encoder (`BAAI/bge-reranker-v2-m3`) rula rigid pe CPU cu consum ridicat de procesor (~250% CPU timp de 10-15s per căutare) sau necesita restart manual de container pentru a fi trecut pe CUDA.
    - Lipsa controlului în panoul de administrare asupra modelului de reranking și a dispozitivului de execuție.
- **Arhitectura actualizată (`backend/core_engine/api/system.py`, `services/rerank_service.py`, `frontend/src/app/dashboard/llm/page.tsx`):**
    - *1. Backend Hot-Reloading (`RerankService.reset_instance()`):*
        - La salvarea setărilor din `/llm/config`, backend-ul resetează instanța singleton de reranker, încărcând dinamic noul model sau dispozitiv fără a întrerupe procesele active și fără a necesita restartul containerului.
        - Detecție automată CUDA cu fallback silențios pe CPU dacă GPU-ul este indisponibil.
    - *2. Admin Interface Card:*
        - Adăugat card dedicat „Neural Reranker (Cross-Encoder)” în `/dashboard/llm`, permițând selectarea dispozitivului (`CPU` - 0 VRAM vs `CUDA/GPU` - ~1.1 GB VRAM pentru latență de ~25ms) și alegerea modelului (`BAAI/bge-reranker-v2-m3`, `large`, `base` sau custom).

### Etapa 47: Anti-Runaway Reasoning Sanitization & Context Headroom Hardening - IMPLEMENTAT (Septembrie 2026)
- **Problemă rezolvată (Eșecul Qwen la sinteza criminalistică Cazul 12):**
    - În timpul investigațiilor atomice multi-țintă, funcția de compactare a contextului (`_compact_evidence_if_needed`) a determinat modelul Qwen să emită raționamentul intern în text brut (`Thinking Process:\n1. Analyze the Request...`) în loc de tag-uri XML `<think>`.
    - Acest monolog a contaminat `working_memory`, iar la etapa de sinteză finală (`_synthesize_final_report`), promptul conținea deja această structură. Qwen a imitat formatul, a generat peste 5.500 de tokeni de meta-gândire în engleză și a izbit frontal limita de context de 8.192 tokeni (`truncated = 1`), eșuând să livreze raportul final în limba română.
- **Arhitectura actualizată (`backend/core_engine/services/chat_service.py`):**
    - *1. Sanitizator Universal (`_sanitize_llm_response`):*
        - Curăță agresiv tag-urile `<think>...</think>` (inclusiv tag-uri neînchise în caz de trunchiere).
        - Detectează și elimină prefixele parazite de meta-gândire (`Thinking Process:`, `Thought Process:`, `Analyze the Request:`).
        - Dacă este specificat un antet-țintă (ex: `target_header="[FACTS]"`), elimină chirurgical orice text sau raționament anterior acestuia.
        - Curăță separatorii comuni (`\n\n---\n\n`, `Concluzie:`, `Final Answer:`).
    - *2. Ancorare Strictă în Prompt (Prefix Enforcement):*
        - În promptul de sinteză finală și în cel de sub-obiective s-a impus directiva critică: „Răspunde DIRECT în limba ROMÂNĂ. Începe răspunsul TĂU STRICT cu primul caracter `[` al secțiunii `[FACTS]`. Este STRICT INTERZIS să generezi 'Thinking Process:', monologuri în engleză sau introduceri meta.”
    - *3. Guardrail în Compactorul de Context:*
        - Dacă compactorul emite meta-gândire contaminată, rezultatul este respins automat și se aplică trunchiere sigură pe dovezile brute deduplicate, protejând `working_memory`.
    - *4. Extindere Context Window la 16.384 Tokeni:*
        - `processing_ctx` a fost ridicat de la 8.192 la 16.384 tokeni (verificat funcțional în VRAM cu 6.5 GB ocupați din 8.2 GB pe RTX 4060).
        - Marja de generare liberă a crescut de la ~2.000 la peste 10.000 de tokeni, eliminând complet riscul de trunchiere.

### Etapa 48: Online Model Ingestion, Smart Archive Extraction & Continuous SSE Stream Resilience - IMPLEMENTAT (Septembrie 2026)
- **Problemă rezolvată:**
    - Procesul de adăugare a modelelor era manual și fragmentat; arhivele `.zip`/`.tar.gz` descărcate necesitau dezarhivare manuală în terminal și comenzi docker care eșuau din backend din lipsa binarului de docker.
    - Secțiunea de import offline era înghesuită în sidebar-ul de 200px, generând overflow și o experiență de utilizare degradată.
    - În timpul raționamentelor lungi ale LLM-ului (ex: 6+ minute la planificarea Qwen), conexiunea HTTP/SSE directă făcea timeout în browser (limita de 180s fără activitate), forțând UI-ul să cadă pe un fallback static galben cu mesaj redundant („Procesul rulează chiar dacă schimbi pagina...”) și pierzând consola de streaming în timp real.
- **Arhitectura actualizată (`backend/core_engine/api/system.py`, `backend/core_engine/api/cases.py`, `frontend/src/app/dashboard/llm/page.tsx`, `frontend/src/app/cases/[id]/page.tsx`):**
    - *1. Online Model Pull & Smart Archive Decompression (`system.py`):*
        - Endpoint `POST /system/models/pull` pentru descărcare directă din registrul Ollama sau HuggingFace (`hf.co/...`), cu streaming nativ de progres în Redis (`POST /api/pull` Ollama) și polling frontend la 1.5s.
        - Endpoint `POST /system/models/import` îmbunătățit cu auto-dezarhivare automată: arhivele `.zip`, `.tar.gz`, `.tgz` sunt extrase într-un director temporar securizat, se scanează recursiv fișierele `.gguf` și se apelează nativ API-ul Ollama (`POST /api/create` cu directiva `from: /root/.ollama/...`), eliminând dependența de docker CLI.
    - *2. Refactorizare Admin UI (`/dashboard/llm/page.tsx`):*
        - Eliminat modulul de import din sidebar-ul îngust; adăugat un card generos cu 2 coloane în corpul principal al paginii (Descărcare Online cu bară de progres live + Fișiere Locale cu detecție tip arhivă/GGUF și badge-uri de stare).
    - *3. Keep-Alive Heartbeat pe Stream-ul de Investigație (`cases.py`):*
        - În `stream()` din `cases.py`, generatorul utilizează `chunk_queue.get(timeout=5.0)`. Dacă în 5 secunde nu sunt emise date (LLM-ul este în plin raționament sau reranking), se emite un pachet ușor `{"type": "ping"}`.
        - Browserul, proxy-ul și uvicorn mențin conexiunea SSE deschisă nelimitat, prevenind deconectările intempestive.
    - *5. Explicit Document & Entity Anchoring (`chat_service.py`):*
        - La interogări în dosare multi-document eterogene, sistemul analizează `user_question` și detectează dacă s-a menționat un fișier specific (ex: `Romgaz_Situatii_Financiare_IFRS_68pag.pdf`) sau o entitate unică.
        - Blochează `target_doc_ids` exclusiv pe documentul indicat, împiedicând filtrul de Macro-Audit Reranking să elimine fișierul țintă sau să aducă fragmente parazite din alte companii din dosar.
    - *6. Header Confidence Level Badge (`page.tsx`):*
        - Parserul extrage robust nivelul de certitudine (`[CONFIDENCE]: HIGH/MEDIUM/LOW`) indiferent de poziționarea pe rând.
        - Afișează un badge proeminent în antetul raportului (verde smarald pulsant pentru HIGH, galben pentru MEDIUM, roșu pentru LOW), oferind inspectorului vizibilitate imediată asupra gradului de încredere probatorie.
    - *7. Enforced JSON Format & Romanian-Native Investigation Planning (`llm_client.py`, `chat_service.py`):*
        - În `UnifiedLLMClient.chat_step()`, s-a adăugat suport universal pentru parametrul `format: Optional[Union[str, dict]] = None`. Pentru Ollama `/api/chat`, trimite direct directiva nativă `format: "json"` (care activează gramatici GBNF forțate în engine-ul de inferență). Pentru LM Studio, vLLM și Ollama OpenAI-compatibil, injectează `response_format: {"type": "json_object"}`.
        - În `AgenticInvestigator._generate_investigation_plan()`, prompt-ul de decompunere a fost rescris 100% în limba română cu regulă strictă de păstrare a termenilor din întrebare (`18 camioane`, bănci, contracte).
        - S-a eliminat complet riscul de „derapaj în engleză” (unde Qwen traducea interogarea în engleză și genera chei de căutare inexistente în OCR precum `18 trucks`), iar planul de investigație este generat instantaneu și parsat cu succes la pasul 1.
    - *8. SOTA Forensic Planning Mega-Prompt & Full Prompt Native Romanian Alignment (`chat_service.py`):*
        - Implementat prompt de planificare de nivel 4 cu matrice de discriminare pe priorități (Prioritate 0: coduri, numere de lot, sume exacte, cantități; Prioritate 1: entități/persoane; Prioritate 2: termeni operativi; Filtru activ de zgomot: elimină cuvintele generice gen „contract”, „document”, „fraudă”, „preț”).
        - Integrat un exemplu structural pur generic (`TRX-909`, `250.000 EUR`, `Compania Alpha`, `Popescu Ion`), validat prin testare live pe container cu zero scurgeri (leakage) și zero halucinații.
        - Eliminat ultimele instanțe de denumiri specifice („șoferul Vasile”, „Mihai Stanciu”) din `compaction_prompt`, respectând 100% mandatul de agnosticism total.
        - Toate mesajele de sistem (`system prompts`) din pașii de execuție sub-ținte și sinteză finală (`_execute_sub_target`, `_synthesize_final_report`, `_compact_evidence_if_needed`) au fost convertite în limba română, eradicând complet bias-ul limbii engleze la modelele open-weights.
    - *9. Clean Text Flow & Sliding Citations Drawer (Varianta C) (`page.tsx`):*
        - S-a eliminat poluarea vizuală cauzată de zecile de etichete `[REF x]` inline din corpul textului: funcția `renderContentWithCitations` curăță acum etichetele de citare și corectează spațierea tipografică, lăsând un raport criminalistic 100% fluid și lizibil.
        - În antetul raportului criminalistic și la subsolul fiecărui mesaj s-a integrat un buton elegant: `🛡️ X Dovezi Verificate`.
        - La click, se deschide un panou lateral glisant (Citations Drawer) cu toate sursele, numerele de pagină și citatele din dosar, permițând deschiderea instantanee a oricărui document direct în viewer-ul PDF.
    - *10. Dual-Tab Execution & Reasoning Drawer (`page.tsx`):*
        - S-au eliminat complet blocurile masive din corpul bulei de chat (`<details>` pentru raționament intern `<think>` și `renderTraceLogs` pentru apelurile de unelte), degajând complet spațiul de lectură.
        - În antetul fiecărui răspuns și în antetul streaming-ului live s-a adăugat butonul `🧠 Consolă AI` (cu contor de unelte apelate).
        - La click, se deschide un panou lateral glisant (580px) cu două tab-uri dedicate:
          1. **Jurnal Execuție:** fluxul complet de căutări, apeluri de unelte (tool calls), parametri și observații;
          2. **Raționament Intern:** monologul intern al modelului (`<think>`) izolat și formatat curat cu scroll independent.

---
*Ultima actualizare: Septembrie 2026 - Adăugat Etapa 46 (Dynamic Neural Reranker Control), Etapa 47 (Anti-Runaway Reasoning Sanitization) și Etapa 48 (Online Model Ingestion, Keep-Alive SSE, SOTA Forensic Mega-Prompt, Citations & AI Trace Drawers).*

### Arhitectura Completa a Sistemului Forensic DocAI (Cum functioneaza)
Sistemul este construit pe un pipeline iterativ cu mai multi pasi (pana la 15), care impune rigoare matematica si de dovezi:
1. **Agentic Investigator Loop:** Sistemul functioneaza printr-o bucla `AgenticInvestigator` care alterneaza faze de rationament (`Thinking`) cu faze de actiune (`Tool Use`). Acest lucru previne halucinatiile deoarece modelul trebuie sa astepte observatia (datele extrase).
2. **Quant Integrity Protocol (Financial Data):** Daca query-ul implica sume (bani), cantitati, bilanturi, agentului i se blocheaza accesul la rezultatele fragmentate ale vector-search-ului. E fortat prin prompt injectat sa apeleze `SEARCH_STRUCTURED_DATA`, care randeaza aggregari din baza de date relationala (PostgreSQL).
3. **Hybrid Search cu Reranker:** Pentru text (contracte, extrase), se apeleaza `SEARCH_TEXT`. Vectorii sunt adusi din extensia `pgvector` (folosind `BAAI/bge-m3`), apoi rerankati cu `BAAI/bge-reranker-v2-m3` (Cross-Encoder multilingv de înaltă rezoluție) pentru a asigura densitatea si relevanta informatiei.
4. **Early Stop Mechanism:** Agentul nu e fortat sa ajunga la pasul 15. Imediat ce are `[FACTS]` complete care raspund integral la intrebarea utilizatorului, opreste bucla si emite o concluzie.
5. **Graph Search (Harta Documentului):** Utilizand `Neo4j`, cand agentul gaseste entitati (nume de companii), poate extrage conexiunile ierarhice (actionariat, auto-tranzactionare, management overlap).


