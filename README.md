# Forensic DocAI v0.7.0 BETA
**Platformă Avansată de Criminalistică Documentară, Audit Antifraudă & Investigații Financiare**

---

## 🚀 Ghid Rapid de Deploy pe un Calculator Nou (via GitHub)

Dacă vrei să rulezi DocAI pe o stație nouă conectată la internet folosind **LM Studio** ca server LLM, **depozitul GitHub este 100% suficient**. Nu este necesar transferul de arhive masive sau modele pe stick.

### 📋 Cerințe Prealabile
1. **Git** instalat.
2. **Docker** și **Docker Compose** (v2.x recomandat).
3. **LM Studio** instalat pe același calculator sau pe un alt calculator din rețeaua locală.

---

### Pasul 1: Clonarea Proiectului
```bash
git clone git@github.com:fl0r90/DOCAI.git
cd DOCAI
```
*(sau via HTTPS: `git clone https://github.com/fl0r90/DOCAI.git`)*

---

### Pasul 2: Ridicarea Containerelor Docker
Rulează comanda de build și pornire în fundal:
```bash
docker compose up -d --build
```
> **Ce face această comandă automat:**
> - Descarcă imaginile oficiale de infrastructură: **PostgreSQL (`pgvector`)**, **Redis 7**, **Neo4j 5**.
> - Construiește local containerele **Backend (FastAPI)**, **Worker (Ingestie)** și **Frontend (Next.js)**.
> - Baza de date inițializează automat tabelele relaționale, vectoriale și utilizatorii default.
> - Embeddings-urile (`BAAI/bge-m3`) și modelele OCR (`RapidOCR`/`Docling`) se vor descărca automat pe CPU la prima solicitare.

---

### Pasul 3: Autentificare în Interfață
1. Deschide browserul la: **`http://localhost:3000`**
2. Autentifică-te cu contul de administrator implicit:
   - **Utilizator:** `admin`
   - **Parolă:** `admin`
   *(La prima logare, sistemul îți va solicita să setezi o parolă nouă securizată).*

---

### Pasul 4: Conectarea la LM Studio
1. Asigură-te că în **LM Studio**:
   - Ai încărcat un model (ex: *Qwen 2.5 14B / 32B*, *Gemma 2*, *Llama 3* etc.).
   - Serverul local este pornit (*Developer Tab* -> *Start Server*, port implicit `1234`).
2. În interfața **DocAI**:
   - Mergi în meniul din dreapta-sus: **System** $\rightarrow$ **Configurație LLM** (`/dashboard/llm`).
   - Selectează motorul: **LM Studio**.
   - Setează adresa endpoint-ului:
     - Dacă LM Studio rulează pe **același calculator cu Docker**:
       ```text
       http://host.docker.internal:1234/v1
       ```
     - Dacă LM Studio rulează pe un **alt calculator din rețea**:
       ```text
       http://IP_CALCULATOR_LM:1234/v1
       ```
   - Apasă pe butonul **„Verifică Conexiunea”** (va detecta latența și va sincroniza automat modelul încărcat către toți experții).
   - Apasă **„Salvează Configurația”**.

---

## ⚙️ Configurare Hardware (Nvidia GPU vs. Doar CPU)

### Cazul A: Calculatorul are placă video Nvidia
- Asigură-te că ai instalat pachetul **NVIDIA Container Toolkit**:
  ```bash
  sudo apt-get install -y nvidia-container-toolkit
  sudo nvidia-ctk runtime configure --runtime=docker
  sudo systemctl restart docker
  ```

### Cazul B: Calculatorul este un Laptop / PC Office (fără placă video Nvidia)
Deoarece raționamentul LLM este descărcat către serverul LM Studio, iar embeddings-urile rulează automat pe CPU, **nu ai nevoie obligatoriu de GPU Nvidia** pe stația de DocAI.
- Dacă Docker raportează `unknown or invalid runtime name: nvidia`, deschide fișierul `docker-compose.yml` și comentează sau șterge liniile:
  ```yaml
  # runtime: nvidia
  ```
  precum și blocurile:
  ```yaml
  # deploy:
  #   resources:
  #     reservations:
  #       devices:
  #         - driver: nvidia
  #           count: all
  #           capabilities: [gpu]
  ```
- Repornește cu `docker compose up -d`.

---

## 🛡️ Credențiale Implicite Sistem

| Rol | Utilizator Implicit | Parolă Implicită | Rol & Permisiuni |
| :--- | :--- | :--- | :--- |
| **ADMIN** | `admin` | `admin` | Acces la Dashboard, Metrici Hardware, Configurație LLM, Backups, Gestiune Useri. |
| **MASTER** | `master` | `master` | Creare și ștergere dosare, management probe, generare rapoarte forensic PDF. |
| **WORKER** | Creat din Admin | La alegere | Vizualizare și lucru exclusiv în dosarele atribuite. |

---

## 🛠️ Comenzi Utile de Administrare

```bash
# Oprire completă a platformei
docker compose down

# Pornire rapidă fără rebuild
docker compose up -d

# Vizualizare loguri în timp real (ex: backend sau worker)
docker compose logs -f backend
docker compose logs -f worker

# Verificare stare containere
docker compose ps
```
