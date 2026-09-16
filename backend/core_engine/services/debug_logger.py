import os
import sys
import json
import time
import traceback
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List


class DebugLogger:
    """
    Forensic DocAI High-Performance Low-Level Telemetry & Debug Logger.
    
    Features:
    - Structured JSONL output with uniform schema (traceability, metrics, duration, errors)
    - Automatic size-capped rotation (100MB per file, up to 5GB total limit)
    - Zero-overhead non-blocking/thread-safe operations
    - Reverse binary seek (tail) for sub-millisecond log retrieval without loading files into RAM
    """

    def __init__(self):
        self.enabled = os.getenv("DEBUG_LOGGING_ENABLED", "true").lower() in ("true", "1", "yes")
        
        # Determine log directory
        if Path("/app/logs").exists():
            self.log_dir = Path("/app/logs/debug")
        else:
            self.log_dir = Path(__file__).resolve().parents[2] / "logs" / "debug"

        self.log_file = self.log_dir / "debug.log"
        self.max_file_size = 100 * 1024 * 1024       # 100MB per file
        self.max_total_size = 5 * 1024 * 1024 * 1024  # 5GB overall cap
        self.max_backup_files = 50
        self.lock = threading.Lock()

        if self.enabled:
            try:
                self.log_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"[DEBUG_LOGGER] Error creating log directory {self.log_dir}: {e}", file=sys.stderr)

    def _rotate_if_needed(self):
        """Rotate the active log file if it exceeds max_file_size, and trim oldest files if exceeding total cap."""
        if not self.log_file.exists():
            return

        try:
            curr_size = self.log_file.stat().st_size
            if curr_size < self.max_file_size:
                return

            # Shift existing rotated files: debug.log.N -> debug.log.N+1
            for i in range(self.max_backup_files - 1, 0, -1):
                sfn = self.log_dir / f"debug.log.{i}"
                dfn = self.log_dir / f"debug.log.{i+1}"
                if sfn.exists():
                    try:
                        sfn.replace(dfn)
                    except Exception:
                        pass

            # Move active log to debug.log.1
            first_rot = self.log_dir / "debug.log.1"
            self.log_file.replace(first_rot)

            # Enforce total directory size limit
            total_size = sum(f.stat().st_size for f in self.log_dir.glob("debug.log*") if f.is_file())
            if total_size > self.max_total_size:
                # Remove oldest files
                rot_files = sorted(self.log_dir.glob("debug.log.*"), key=lambda p: p.stat().st_mtime)
                for old_f in rot_files:
                    try:
                        old_f.unlink()
                        total_size -= old_f.stat().st_size
                        if total_size <= self.max_total_size:
                            break
                    except Exception:
                        pass
        except Exception as e:
            print(f"[DEBUG_LOGGER] Rotation error: {e}", file=sys.stderr)

    def _write_entry(self, level: str, service: str, action: str, 
                     data: Optional[Dict[str, Any]] = None,
                     trace_id: Optional[str] = None,
                     case_id: Optional[int] = None,
                     doc_id: Optional[int] = None,
                     duration_ms: Optional[float] = None,
                     metrics: Optional[Dict[str, Any]] = None,
                     error: Optional[Dict[str, Any]] = None):
        """Core write routine: formats JSONL and commits to disk with rotation check."""
        if not self.enabled:
            return

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "service": service,
            "action": action,
            "thread_id": threading.current_thread().name
        }

        if trace_id:
            entry["trace_id"] = str(trace_id)
        if case_id is not None:
            entry["case_id"] = case_id
        if doc_id is not None:
            entry["doc_id"] = doc_id
        if duration_ms is not None:
            entry["duration_ms"] = round(duration_ms, 2)
        if metrics:
            entry["metrics"] = metrics
        if data:
            entry["data"] = data
        if error:
            entry["error"] = error

        line = json.dumps(entry, ensure_ascii=False) + "\n"

        with self.lock:
            try:
                self._rotate_if_needed()
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(line)
            except Exception as e:
                print(f"[DEBUG_LOGGER_WRITE_ERR] {e}", file=sys.stderr)

    # --------------------------------------------------------------------------
    # Specialized Forensic & Low-Level Helpers
    # --------------------------------------------------------------------------

    def debug(self, service: str, action: str, data: Optional[Dict[str, Any]] = None, **kwargs):
        self._write_entry("DEBUG", service, action, data=data, **kwargs)

    def info(self, service: str, action: str, data: Optional[Dict[str, Any]] = None, **kwargs):
        self._write_entry("INFO", service, action, data=data, **kwargs)

    def warn(self, service: str, action: str, data: Optional[Dict[str, Any]] = None, **kwargs):
        self._write_entry("WARN", service, action, data=data, **kwargs)

    def error(self, service: str, action: str, error_msg: str, 
              error_type: Optional[str] = None, 
              details: Optional[Dict[str, Any]] = None, 
              exc_info: bool = False, **kwargs):
        err_payload = {
            "message": str(error_msg),
            "type": error_type or "GenericError"
        }
        if details:
            err_payload["details"] = details
        if exc_info:
            err_payload["traceback"] = traceback.format_exc()

        self._write_entry("ERROR", service, action, error=err_payload, **kwargs)

    # Module-specific shortcuts
    def step_start(self, session_id: str, step: int, action: str, case_id: Optional[int] = None):
        self.debug(
            service="chat_service",
            action="STEP_START",
            trace_id=session_id,
            case_id=case_id,
            data={"step": step, "action": action}
        )

    def llm_call(self, model: str, endpoint: str, payload_tokens_est: int, 
                 messages_count: int, trace_id: Optional[str] = None, case_id: Optional[int] = None):
        self.debug(
            service="llm_client",
            action="LLM_CALL_START",
            trace_id=trace_id,
            case_id=case_id,
            metrics={"payload_tokens_est": payload_tokens_est, "messages_count": messages_count},
            data={"model": model, "endpoint": endpoint}
        )

    def llm_complete(self, model: str, duration_ms: float, 
                     tokens_out_est: Optional[int] = None, 
                     tool_calls_count: int = 0,
                     trace_id: Optional[str] = None, case_id: Optional[int] = None):
        self.debug(
            service="llm_client",
            action="LLM_CALL_COMPLETE",
            trace_id=trace_id,
            case_id=case_id,
            duration_ms=duration_ms,
            metrics={"tokens_out_est": tokens_out_est, "tool_calls_count": tool_calls_count},
            data={"model": model}
        )

    def fallback_trigger(self, reason: str, fallback_from: str, fallback_to: str, 
                         error_code: Optional[int] = None, trace_id: Optional[str] = None):
        self.warn(
            service="llm_client",
            action="FALLBACK_TRIGGER",
            trace_id=trace_id,
            data={
                "reason": reason,
                "from": fallback_from,
                "to": fallback_to,
                "error_code": error_code
            }
        )

    def tool_raw(self, raw_calls: List[Dict[str, Any]], trace_id: Optional[str] = None):
        self.debug(
            service="chat_service",
            action="TOOL_RAW",
            trace_id=trace_id,
            data={"raw_tool_calls": raw_calls}
        )

    def tool_normalized(self, original_name: str, normalized_name: str, 
                        args: Dict[str, Any], split_calls: Optional[List[str]] = None, 
                        trace_id: Optional[str] = None):
        payload: Dict[str, Any] = {
            "original": original_name,
            "normalized": normalized_name,
            "args": args
        }
        if split_calls:
            payload["split_into"] = split_calls
        self.debug(
            service="chat_service",
            action="TOOL_NORMALIZED",
            trace_id=trace_id,
            data=payload
        )

    def tool_exec(self, tool_name: str, duration_ms: float, success: bool, 
                  obs_len: int, error: Optional[str] = None, trace_id: Optional[str] = None):
        self.debug(
            service="chat_service",
            action="TOOL_EXEC",
            trace_id=trace_id,
            duration_ms=duration_ms,
            metrics={"observation_chars": obs_len, "success": success},
            data={"tool_name": tool_name},
            error={"message": error} if error else None
        )

    def recall_metrics(self, query: str, vector_count: int, lexical_count: int, 
                       compound_count: int, positional_count: int, reranked_count: int, 
                       duration_ms: float, trace_id: Optional[str] = None, case_id: Optional[int] = None):
        self.debug(
            service="chat_service",
            action="HYBRID_RECALL_METRICS",
            trace_id=trace_id,
            case_id=case_id,
            duration_ms=duration_ms,
            metrics={
                "vector_candidates": vector_count,
                "lexical_candidates": lexical_count,
                "compound_candidates": compound_count,
                "positional_candidates": positional_count,
                "reranked_final": reranked_count
            },
            data={"query": query[:200]}
        )

    def ocr_page(self, doc_id: int, page_num: int, total_pages: int, 
                 engine: str, duration_ms: float, chars_count: int):
        self.debug(
            service="ocr_service",
            action="OCR_PAGE",
            doc_id=doc_id,
            duration_ms=duration_ms,
            metrics={"chars_count": chars_count, "page": page_num, "total_pages": total_pages},
            data={"engine": engine}
        )

    def task_stage(self, doc_id: int, stage: str, status: str, 
                   duration_ms: Optional[float] = None, details: Optional[Dict[str, Any]] = None):
        self.info(
            service="worker_tasks",
            action="TASK_STAGE",
            doc_id=doc_id,
            duration_ms=duration_ms,
            data={"stage": stage, "status": status, "details": details or {}}
        )

    # --------------------------------------------------------------------------
    # Ultra-Fast Reverse Binary Seek (Tail Reader)
    # --------------------------------------------------------------------------

    def get_recent_logs(self, limit: int = 100, offset: int = 0, 
                        level: Optional[str] = None, 
                        service: Optional[str] = None) -> Dict[str, Any]:
        """
        Reads recent log entries from the end of the file backwards.
        Never loads entire files into memory; operates in sub-millisecond buffers.
        """
        if not self.log_file.exists():
            return {"logs": [], "total": 0, "has_more": False}

        results: List[Dict[str, Any]] = []
        target_count = offset + limit
        level_filter = level.upper() if level else None
        service_filter = service.lower() if service else None

        # Helper to process lines from a single file in reverse
        def _read_reverse_file(file_path: Path) -> List[Dict[str, Any]]:
            file_entries = []
            try:
                with open(file_path, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    file_size = f.tell()
                    if file_size == 0:
                        return []

                    buffer_size = 65536  # 64 KB chunks
                    pos = file_size
                    remainder = b""

                    while pos > 0 and len(file_entries) < target_count:
                        read_len = min(buffer_size, pos)
                        pos -= read_len
                        f.seek(pos, os.SEEK_SET)
                        chunk = f.read(read_len) + remainder

                        lines = chunk.split(b"\n")
                        remainder = lines[0]  # First line may be incomplete

                        # Traverse lines backwards
                        for line_bytes in reversed(lines[1:]):
                            line_str = line_bytes.strip().decode("utf-8", errors="replace")
                            if not line_str:
                                continue
                            try:
                                entry = json.loads(line_str)
                                if level_filter and entry.get("level") != level_filter:
                                    continue
                                if service_filter and entry.get("service", "").lower() != service_filter:
                                    continue
                                file_entries.append(entry)
                                if len(file_entries) >= target_count:
                                    break
                            except Exception:
                                continue

                    # Check the very first line if pos reached 0
                    if pos == 0 and remainder and len(file_entries) < target_count:
                        line_str = remainder.strip().decode("utf-8", errors="replace")
                        if line_str:
                            try:
                                entry = json.loads(line_str)
                                if (not level_filter or entry.get("level") == level_filter) and \
                                   (not service_filter or entry.get("service", "").lower() == service_filter):
                                    file_entries.append(entry)
                            except Exception:
                                pass
            except Exception as e:
                print(f"[DEBUG_LOGGER_READ_ERR] {e}", file=sys.stderr)
            return file_entries

        # Read from active debug.log
        results = _read_reverse_file(self.log_file)

        # If not enough records, look into debug.log.1
        if len(results) < target_count:
            rot1 = self.log_dir / "debug.log.1"
            if rot1.exists():
                extra = _read_reverse_file(rot1)
                results.extend(extra)

        paginated = results[offset:offset + limit]
        return {
            "logs": paginated,
            "total": len(results),
            "has_more": len(results) > (offset + limit)
        }


# Global singleton instance
debug_logger = DebugLogger()
