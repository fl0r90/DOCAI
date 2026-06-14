# Harta Sistemului Forensic DocAI v0.3.0

Acest document descrie arhitectura de date și uneltele de investigație disponibile Agentului AI pentru analiza documentelor complexe în regim offline.

---

## 1. INFRASTRUCTURA DE DATE (BAZE DE DATE)

Sistemul utilizează un model de stocare hibrid pentru a permite atât căutări granulare (cifre), cât și analize macro (relații).

### A. PostgreSQL (forensic_db) - "Sursa de Adevăr și Memoria Textuală"
Este baza de date principală, optimizată pentru căutări hibride (Full-Text + Vectorial).
*   **Tabelul `documents`**: Stochează metadatele fișierelor (nume, hash, tip: FACTURA, EXTRAS_CONT, RAPORT).
*   **Tabelul `document_chunks`**: Conține textul brut spart în fragmente (pagini/paragrafe).
    *   *Vector Embeddings*: Fiecare fragment are un vector asociat pentru căutare semantică (intuiție).
    *   *Spatial Metadata*: Coordonate [x, y, w, h] pentru a identifica exact locul în PDF.
*   **Tabelul `financial_items`**: **CRITIC.** Conține datele extrase structural din tabelele PDF (Data, Descriere, Sumă, Monedă). Este folosit pentru auditul matematic precis.
*   **Tabelul `master_entities`**: Registrul de entități identificate (CUI, IBAN, Nume Firme, Persoane) și legăturile lor cu documentele.

### B. Neo4j - "Harta Documentului și Graf de Tranzacții"
Bază de date orientată pe grafuri, folosită pentru a înțelege structura ierarhică.
*   **Ierarhie**: Reprezintă vizual legătura: `Document` -> `Section` -> `Page` -> `Chunk`.
*   **Relații**: Maparea fluxurilor de bani între entități (cine a plătit către cine, pe baza extraselor).
*   **Macro-Navigation**: Permite Agentului să "vadă" structura unui raport de 500 pagini fără a citi tot textul.

### C. Redis - "Sistemul de Nervi și Cozi"
*   **Task Queue**: Gestionează ordinea în care documentele sunt procesate de Worker.
*   **Processing State**: Reține progresul în timp real (ex: "Pagina 45/100 procesată").
*   **Cache**: Buffer pentru rezultatele intermediare de căutare.

---

## 2. UNELTELE DE INVESTIGAȚIE (AGENT TOOLS)

Agentul AI nu doar "citește" text, ci interoghează activ aceste baze de date folosind următoarele unelte:

### I. SEARCH(keywords) - "Căutarea Robustă"
*   **Funcționare**: Extrage automat cuvintele cheie din cererea LLM-ului.
*   **Ranking Hibrid**: Caută în `document_chunks` și prioritizează fragmentele care conțin cele mai multe potriviri.
*   **Context Zoom**: Când găsește un rezultat, unealta aduce automat și fragmentele vecine (pagina anterioară/următoare) pentru a oferi context complet.
*   **Agnosticism**: Funcționează pe orice subiect fără a avea pre-definite nume de firme sau persoane.

### II. CALCULATE(expression) - "Auditul Matematic"
*   **Funcționare**: Trimite expresii matematice către un motor determinist (Python).
*   **Scop**: Elimină halucinațiile numerice ale LLM-ului. Dacă Agentul găsește 3 facturi, el va cere `CALCULATE(sum_1 + sum_2 + sum_3)` pentru a returna un total garantat corect.

### III. GET_PAGE_CONTEXT (Infrastructură Neo4j)
*   **Funcționare**: Permite Agentului să solicite vizualizarea unei pagini întregi dacă a găsit un indiciu într-un fragment mic.
*   **Utilitate**: Esențial pentru tabelele care se întind pe mai multe pagini.

---

## 3. LOGICA DE INVESTIGAȚIE (FLOW-UL AGENTULUI)

1.  **Analiza Întrebării**: Agentul primește întrebarea și consultă "Harta Aplicației".
2.  **Decizie de Căutare**: Dacă nu are date în context, apelează `SEARCH`.
3.  **Observație**: Primește rezultatele brute (Text + SQL Financial Data).
4.  **Raționament (Reasoning)**: Verifică dacă datele sunt suficiente. Dacă vede o discrepanță între două sume, poate decide un nou pas de căutare.
5.  **Calcul**: Folosește `CALCULATE` pentru orice agregare de date.
6.  **Răspuns Final**: Formulează concluzia în Română, citând sursele sub forma `[Source ID, Page X]`.

---
*Acest sistem este proiectat să funcționeze 100% offline, respectând confidențialitatea datelor forensic.*
