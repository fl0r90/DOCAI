# Flux Detaliat Ingestie Documente (Forensic DocAI)

Acest document descrie pas cu pas ce se întâmplă cu un fișier din momentul încărcării până când devine interogabil.

---

## PASUL 1: Upload (Frontend & Backend API)
1.  **Utilizatorul** alege un fișier (PDF/Imagine) în interfața Next.js și apasă "Încarcă".
2.  **Frontend-ul** trimite un `POST` către `/api/cases/{id}/documents`.
3.  **Backend-ul (FastAPI)**:
    - Salvează fișierul fizic în `shared_uploads/`.
    - Creează o înregistrare în PostgreSQL (tabelul `documents`) cu status `QUEUED`.
    - Calculează un `file_hash` pentru a preveni procesarea duplicat.
4.  **Redis**: Backend-ul pune un mesaj în coada de procesare Redis (`process_document_task`).

---

## PASUL 2: Procesarea Worker (Inima Sistemului)
Worker-ul (Python) rulează în fundal și monitorizează Redis. Când vede un task:

### 2.1. OCR Structural (Docling / Table Transformer)
- Fișierul este trimis către serviciul de OCR.
- **Docling** sparge documentul în elemente structurale: Titluri, Paragrafe și **Tabele**.
- Rezultatul este un format Markdown curățat care păstrează alinierea vizuală.

### 2.2. Indexarea Textuală (PostgreSQL `document_chunks`)
- Textul este spart în fragmente (chunks) de aprox. 1000-2000 caractere.
- Fiecare fragment primește **Coordonate Spațiale** [x,y,w,h].
- Se generează **Vector Embeddings** folosind un model local (ex: `mxbai-embed-large`) și sunt salvate în `document_chunks` (coloana `embedding` de tip `vector`).

### 2.3. Extracția Financiară (Punctul Critic de Eșec)
Aici sistemul încearcă să transforme textul brut în date SQL structurate (`financial_items`):
1.  **Metoda Regex**: Folosește un pattern pentru a identifica rândurile de tabel (`| Data | Descriere | Debit | ...`).
2.  **Logica de Ghicire**: Deoarece extrasele de cont au coloane diferite, Worker-ul folosește indici relativi:
    - `amounts[-3]` -> Considerat DEBIT.
    - `amounts[-2]` -> Considerat CREDIT.
    - `amounts[-1]` -> Considerat SOLD (Balanță).
3.  **EROARE IDENTIFICATĂ**: Dacă un extras are o coloană în plus sau în minus, sistemul "decalează" coloanele și salvează Soldul în locul Debitului. Acest lucru a poluat baza de date în testul nostru.

### 2.4. Rezoluția Entităților & Graf (Neo4j)
- Sistemul extrage IBAN-uri, CUI-uri și nume de firme din text.
- **Normalizare**: Curăță caracterele speciale.
- **Sync Neo4j**: Creează noduri de tip `Firma` sau `Cont_Bancar` și relații de tip `A_VIRAT` sau `APARE_IN`.

### 2.5. Generarea Rezumatului (AI Summary)
- LLM-ul (Gemma/Mistral) primește textul întreg și generează un rezumat ierarhic care este salvat în tabelul `documents`.

---

## PASUL 3: Interogarea (Chat Agentic)
Când pui o întrebare în chat:
1.  **Agentul** citește întrebarea.
2.  **Decizie**: Agentul alege ce unealtă să folosească (acum are `SEARCH_TRANSACTIONS` și `SEARCH_TEXT`).
3.  **Conflict**: Dacă Agentul alege `SEARCH_TRANSACTIONS`, el primește datele "poluate" de la Pasul 2.3. Dacă alege `SEARCH_TEXT`, el "vede" tabelul corect dar trebuie să-l parseze singur.

---

## CONCLUZIE: Unde trebuie reparat?
Problema nu este la AI, ci la **Pasul 2.3 (Extracția Financiară)**. Logica de tip "ghicim coloana după index" este prea fragilă pentru extrase de cont variate. 

**Soluția viitoare:** LLM-ul ar trebui să analizeze capul de tabel la procesare și să determine dinamic care coloană este "Debit" și care e "Sold".
