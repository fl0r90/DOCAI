import os
import time
import json
import threading
from typing import Optional

try:
    import fitz
except ImportError:
    fitz = None

class DocProgressTracker:
    """
    Sistem dinamic de calcul ETA și urmărire a progresului pentru procesarea documentelor.
    Asigură:
    1. Estimare inițială bazată pe numărul real de pagini (PyMuPDF).
    2. Ticker de fundal pentru actualizare în timp real (countdown ETA și incrementare fină a procentului).
    3. Măsurare adaptivă a vitezei (secunde/pagină, secunde/chunk, secunde/tabel).
    4. Numărare granulară a segmentelor (pagini/chunks/tabele) pentru a preveni 'undefined / undefined'.
    """

    def __init__(self, doc_id: int, filename: str, file_path: str, redis_client=None):
        self.doc_id = doc_id
        self.filename = filename
        self.file_path = file_path
        
        if redis_client:
            self.r = redis_client
        else:
            import redis
            self.r = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

        # 1. Număr real de pagini
        self.total_pages = self._detect_page_count()
        
        # 2. Benchmark-uri empirice (ajustate adaptiv)
        self.sec_per_page = 2.5
        self.sec_per_chunk = 0.08
        self.sec_overview = 14.0
        self.sec_per_table = 9.0
        self.sec_finalize = 3.0

        # Estimări inițiale pe etape
        self.est_ocr_time = max(4.0, self.total_pages * self.sec_per_page)
        self.est_rag_time = max(3.0, self.total_pages * 3 * self.sec_per_chunk)
        self.est_grinder_time = self.sec_overview + self.sec_finalize
        self.total_est_duration = self.est_ocr_time + self.est_rag_time + self.est_grinder_time

        # Stare curentă
        self.current_phase = "INIT"
        self.percent = 5.0
        self.eta_seconds = int(self.total_est_duration)
        self.current_segment = 1
        self.total_segments = max(1, self.total_pages)
        self.message = f"Inițializare ({self.total_pages} pagini)..."

        # Ticker de fundal (thread-safe)
        self._ticker_thread: Optional[threading.Thread] = None
        self._stop_ticker = threading.Event()
        self._lock = threading.Lock()
        
        self.pipeline_start = time.time()
        self.phase_start = time.time()
        self.actual_ocr_time = 0.0

        # Segmente dinamice
        self.total_chunks = 0
        self.total_tables = 0

    def _detect_page_count(self) -> int:
        if not self.file_path or not os.path.exists(self.file_path):
            return 1
        if self.file_path.lower().endswith(".pdf") and fitz:
            try:
                with fitz.open(self.file_path) as doc:
                    return max(1, doc.page_count)
            except Exception as e:
                print(f"[!] Eroare fitz la detectare pagini pentru {self.file_path}: {e}")
        return 1

    def _publish(self):
        """Scrie starea curentă în Redis sub cheia doc_progress_{doc_id}."""
        with self._lock:
            payload = {
                "status": self.current_phase,
                "percent": round(float(self.percent), 1),
                "eta_seconds": max(0, int(self.eta_seconds)),
                "current_segment": int(self.current_segment),
                "total_segments": max(1, int(self.total_segments)),
                "message": str(self.message)
            }
            try:
                self.r.set(f"doc_progress_{self.doc_id}", json.dumps(payload), ex=86400)
            except Exception as e:
                print(f"[!] Eroare la publicarea progresului în Redis: {e}")

    def _stop_active_ticker(self):
        """Oprește thread-ul de fundal dacă este activ."""
        if self._ticker_thread and self._ticker_thread.is_alive():
            self._stop_ticker.set()
            self._ticker_thread.join(timeout=1.5)
        self._stop_ticker.clear()
        self._ticker_thread = None

    # ==================== ETAPA 1: OCR (DOCLING) ====================

    def start_ocr_phase(self):
        """Pornire etapă OCR cu ticker de fundal pentru countdown live."""
        self._stop_active_ticker()
        self.current_phase = "DOCLING_OCR"
        self.phase_start = time.time()
        self.current_segment = 1
        self.total_segments = self.total_pages
        self.percent = 5.0
        self.eta_seconds = int(self.est_ocr_time + self.est_rag_time + self.est_grinder_time)
        self.message = f"OCR structural Docling ({self.total_pages} pag)..."
        self._publish()

        def _ocr_ticker():
            while not self._stop_ticker.is_set():
                time.sleep(1.0)
                if self._stop_ticker.is_set():
                    break
                elapsed = time.time() - self.phase_start
                if elapsed < self.est_ocr_time:
                    fraction = elapsed / self.est_ocr_time
                    rem_ocr = self.est_ocr_time - elapsed
                    cur_page = min(self.total_pages, max(1, int(1 + fraction * self.total_pages)))
                else:
                    overtime = elapsed - self.est_ocr_time
                    fraction = 0.95
                    rem_ocr = max(2.0, 6.0 / (1.0 + 0.15 * overtime))
                    cur_page = self.total_pages

                with self._lock:
                    self.percent = 5.0 + fraction * 33.0  # Urcă până la ~38%
                    self.eta_seconds = int(rem_ocr + self.est_rag_time + self.est_grinder_time)
                    self.current_segment = cur_page
                    self.message = f"OCR structural Docling (pag. ~{cur_page}/{self.total_pages})..."
                self._publish()

        self._ticker_thread = threading.Thread(target=_ocr_ticker, daemon=True)
        self._ticker_thread.start()

    def finish_ocr_phase(self, num_tables: int = 0):
        """Finalizare etapă OCR și calibrare durate viitoare."""
        self._stop_active_ticker()
        self.actual_ocr_time = max(1.0, time.time() - self.phase_start)
        if self.total_pages > 0:
            self.sec_per_page = self.actual_ocr_time / self.total_pages
        
        self.total_tables = num_tables
        self.est_grinder_time = self.sec_overview + (num_tables * self.sec_per_table) + self.sec_finalize

        with self._lock:
            self.percent = 40.0
            self.current_segment = self.total_pages
            self.total_segments = self.total_pages
            self.eta_seconds = int(self.est_rag_time + self.est_grinder_time)
            self.message = "OCR finalizat. Pregătire indexare vectorială..."
        self._publish()

    # ==================== ETAPA 2: RAG (INDEXARE VECTORIALĂ) ====================

    def start_rag_phase(self, total_chunks: int):
        """Pornire indexare vectorială pe chunks."""
        self._stop_active_ticker()
        self.current_phase = "RAG_INGESTING"
        self.phase_start = time.time()
        self.total_chunks = max(1, total_chunks)
        self.total_segments = self.total_chunks
        self.current_segment = 0
        self.est_rag_time = max(2.0, self.total_chunks * self.sec_per_chunk)

        with self._lock:
            self.percent = 40.0
            self.eta_seconds = int(self.est_rag_time + self.est_grinder_time)
            self.message = f"Indexare vectorială (0/{self.total_chunks} chunks)..."
        self._publish()

    def update_rag_chunk(self, chunk_idx: int):
        """Actualizare progres la fiecare chunk procesat."""
        elapsed = max(0.1, time.time() - self.phase_start)
        avg_chunk = elapsed / max(1, chunk_idx)
        rem_chunks = max(0, self.total_chunks - chunk_idx)
        rem_rag = rem_chunks * avg_chunk

        with self._lock:
            fraction = min(1.0, chunk_idx / max(1, self.total_chunks))
            self.percent = 40.0 + fraction * 20.0  # 40% -> 60%
            self.current_segment = chunk_idx
            self.total_segments = self.total_chunks
            self.eta_seconds = int(rem_rag + self.est_grinder_time)
            self.message = f"Indexare vectorială ({chunk_idx}/{self.total_chunks} chunks)..."
        self._publish()

    def finish_rag_phase(self):
        """Finalizare indexare vectorială."""
        with self._lock:
            self.percent = 60.0
            self.current_segment = self.total_chunks
            self.total_segments = self.total_chunks
            self.eta_seconds = int(self.est_grinder_time)
            self.message = "Indexare vectorială finalizată."
        self._publish()

    # ==================== ETAPA 3: AI GRINDER (EXTRACTIE FORENSICA) ====================

    def start_grinder_overview(self, total_tables: int = 0):
        """Extracție macro / atribute dinamice cu LLM cu ticker de fundal."""
        self._stop_active_ticker()
        self.current_phase = "AI_EXTRACTING"
        self.phase_start = time.time()
        self.total_tables = total_tables
        self.total_segments = 1 + total_tables
        self.current_segment = 1
        
        rem_tables_time = total_tables * self.sec_per_table + self.sec_finalize
        self.est_grinder_time = self.sec_overview + rem_tables_time

        with self._lock:
            self.percent = 60.0
            self.eta_seconds = int(self.est_grinder_time)
            self.message = f"Audit structurat & clasificare ({self.filename})..."
        self._publish()

        def _overview_ticker():
            while not self._stop_ticker.is_set():
                time.sleep(1.0)
                if self._stop_ticker.is_set():
                    break
                elapsed = time.time() - self.phase_start
                if elapsed < self.sec_overview:
                    fraction = elapsed / self.sec_overview
                    rem_over = self.sec_overview - elapsed
                else:
                    overtime = elapsed - self.sec_overview
                    fraction = 0.95
                    rem_over = max(2.0, 5.0 / (1.0 + 0.2 * overtime))

                with self._lock:
                    self.percent = 60.0 + fraction * 12.0  # 60% -> ~72%
                    self.eta_seconds = int(rem_over + rem_tables_time)
                    self.current_segment = 1
                    self.message = f"Audit structurat & clasificare LLM..."
                self._publish()

        self._ticker_thread = threading.Thread(target=_overview_ticker, daemon=True)
        self._ticker_thread.start()

    def finish_grinder_overview(self):
        self._stop_active_ticker()
        with self._lock:
            self.percent = 72.0
            self.current_segment = 1
            self.total_segments = 1 + self.total_tables
            rem_tables_time = self.total_tables * self.sec_per_table + self.sec_finalize
            self.eta_seconds = int(rem_tables_time)
            self.message = "Clasificare finalizată. Analiză entități & tabele..."
        self._publish()

    def start_grinder_table(self, table_idx: int, total_tables: int):
        """Pornire ticker pentru auditarea fiecărui tabel găsit."""
        self._stop_active_ticker()
        self.current_phase = "AI_EXTRACTING"
        self.phase_start = time.time()
        self.total_tables = total_tables
        self.total_segments = 1 + total_tables
        self.current_segment = 2 + table_idx
        
        base_percent = 72.0 + (table_idx / max(1, total_tables)) * 22.0
        rem_tables = max(0, total_tables - table_idx)
        est_rem = rem_tables * self.sec_per_table + self.sec_finalize

        with self._lock:
            self.percent = base_percent
            self.eta_seconds = int(est_rem)
            self.message = f"Audit tabel {table_idx + 1}/{total_tables} (LLM)..."
        self._publish()

        def _table_ticker():
            while not self._stop_ticker.is_set():
                time.sleep(1.0)
                if self._stop_ticker.is_set():
                    break
                elapsed = time.time() - self.phase_start
                fraction = min(0.95, elapsed / max(2.0, self.sec_per_table))
                step_span = 22.0 / max(1, total_tables)
                rem_cur = max(1.0, self.sec_per_table - elapsed)
                total_rem = rem_cur + max(0, total_tables - table_idx - 1) * self.sec_per_table + self.sec_finalize

                with self._lock:
                    self.percent = base_percent + fraction * step_span
                    self.eta_seconds = int(total_rem)
                    self.message = f"Audit tabel {table_idx + 1}/{total_tables} (LLM)..."
                self._publish()

        self._ticker_thread = threading.Thread(target=_table_ticker, daemon=True)
        self._ticker_thread.start()

    def finish_grinder_table(self, table_idx: int, total_tables: int):
        self._stop_active_ticker()
        rem_tables = max(0, total_tables - table_idx - 1)
        with self._lock:
            self.percent = 72.0 + ((table_idx + 1) / max(1, total_tables)) * 22.0
            self.current_segment = 2 + table_idx
            self.eta_seconds = int(rem_tables * self.sec_per_table + self.sec_finalize)
            self.message = f"Tabel {table_idx + 1}/{total_tables} auditat."
        self._publish()

    # ==================== ETAPA 4: SINTEZA & FINALIZARE ====================

    def start_synthesis(self):
        self._stop_active_ticker()
        with self._lock:
            self.current_phase = "AI_EXTRACTING"
            self.percent = 94.0
            self.eta_seconds = 4
            self.message = "Generare sinteză executivă (LLM)..."
        self._publish()

    def start_graph_sync(self):
        self._stop_active_ticker()
        with self._lock:
            self.current_phase = "GRAPH_SYNC"
            self.percent = 97.0
            self.eta_seconds = 2
            self.message = "Sincronizare Graph & Finalizare..."
        self._publish()

    def complete(self):
        """Marchează documentul ca procesat complet cu succes (100%)."""
        self._stop_active_ticker()
        with self._lock:
            self.current_phase = "COMPLETED"
            self.percent = 100.0
            self.eta_seconds = 0
            self.current_segment = self.total_segments
            self.message = "Succes."
        self._publish()

    def fail(self, error_message: str):
        """Marchează documentul ca eșuat."""
        self._stop_active_ticker()
        with self._lock:
            self.current_phase = "FAILED"
            self.percent = 0.0
            self.eta_seconds = 0
            self.message = f"Eroare: {error_message}"
        self._publish()
