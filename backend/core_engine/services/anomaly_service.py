import math
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from .. import models

class FinancialAnomalyService:
    """
    Motor criminalistic avansat de detecție a anomaliilor financiare:
    1. Legea lui Benford (Benford's Law) - calcul MAD și deviații primei cifre
    2. Structurare / Fragmentare plăți (Smurfing / Split-invoicing)
    3. Tranzacții duplicate sau cvasi-duplicate
    4. Tranzacții în zile nelucrătoare (Weekend transactions)
    5. Aglomerare de numere rotunde (Round Number Clustering)
    """

    BENFORD_THEORETICAL = {
        1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097,
        5: 0.079, 6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046
    }

    def analyze_case(self, case_id: int, db: Session) -> Dict[str, Any]:
        items = db.execute(text("""
            SELECT f.id, f.doc_filename, f.doc_number, f.transaction_date, 
                   f.description, f.amount, f.currency, f.doc_type, 
                   f.transaction_type, f.cui_source, f.iban_source, 
                   f.cui_destination, f.iban_destination
            FROM financial_items f
            JOIN documents d ON d.id = f.document_id
            WHERE d.case_id = :case_id AND f.amount IS NOT NULL
            ORDER BY f.created_at ASC
        """), {"case_id": case_id}).fetchall()

        if not items:
            return {
                "case_id": case_id,
                "total_items": 0,
                "risk_score": 0.0,
                "risk_level": "LOW",
                "message": "Nu există elemente financiare extrase pentru acest dosar."
            }

        records = [dict(r._mapping) for r in items]

        benford_res = self._check_benford(records)
        smurfing_res = self._check_smurfing(records)
        duplicate_res = self._check_duplicates(records)
        weekend_res = self._check_weekends(records)
        round_res = self._check_round_numbers(records)

        # Calcul scor global de risc (0 - 100)
        risk_score = 0
        if benford_res["risk_flag"]: risk_score += 25
        if smurfing_res["count"] > 0: risk_score += min(30, smurfing_res["count"] * 10)
        if duplicate_res["count"] > 0: risk_score += min(25, duplicate_res["count"] * 10)
        if round_res["risk_flag"]: risk_score += 15
        if weekend_res["count"] > 0: risk_score += min(10, weekend_res["count"] * 5)

        risk_score = min(100, risk_score)
        risk_level = "CRITICAL" if risk_score >= 70 else "HIGH" if risk_score >= 45 else "MEDIUM" if risk_score >= 20 else "LOW"

        return {
            "case_id": case_id,
            "total_items": len(records),
            "total_volume": round(sum(abs(r.get("amount") or 0.0) for r in records), 2),
            "risk_score": risk_score,
            "risk_level": risk_level,
            "anomalies": {
                "benford_analysis": benford_res,
                "split_invoicing_smurfing": smurfing_res,
                "duplicate_transactions": duplicate_res,
                "round_number_clustering": round_res,
                "weekend_transactions": weekend_res
            }
        }

    def _check_benford(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        counts = {d: 0 for d in range(1, 10)}
        valid_amounts = 0

        for r in records:
            amt = abs(r.get("amount") or 0.0)
            if amt >= 1.0:
                s = str(amt).lstrip('0').replace('.', '')
                if s:
                    first_digit = int(s[0])
                    if 1 <= first_digit <= 9:
                        counts[first_digit] += 1
                        valid_amounts += 1

        if valid_amounts < 15:
            return {
                "applicable": False,
                "valid_samples": valid_amounts,
                "message": "Volum insuficient de tranzacții pentru testul Benford (minim 15 necesare).",
                "risk_flag": False
            }

        observed = {}
        deviations = {}
        mad = 0.0

        for d in range(1, 10):
            obs_ratio = counts[d] / valid_amounts
            theo_ratio = self.BENFORD_THEORETICAL[d]
            dev = abs(obs_ratio - theo_ratio)
            mad += dev
            observed[d] = round(obs_ratio, 3)
            deviations[d] = round(dev, 3)

        mad = round(mad / 9.0, 4)
        # Interpretare conformităţii după standardul Drake & Nigrini (1997)
        risk_flag = mad >= 0.015
        conformity = "Conformitate Strânsă" if mad < 0.006 else \
                     "Conformitate Acceptabilă" if mad < 0.012 else \
                     "Neconformitate Marginală" if mad < 0.015 else "Neconformitate Severă (Posibilă falsificare)"

        return {
            "applicable": True,
            "valid_samples": valid_amounts,
            "mad_score": mad,
            "conformity": conformity,
            "risk_flag": risk_flag,
            "observed_frequencies": observed,
            "theoretical_frequencies": self.BENFORD_THEORETICAL,
            "deviations": deviations
        }

    def _check_smurfing(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Căutăm tranzacții în proximitatea pragurilor de raportare:
        # Prag 1: 40.000 - 49.999 RON (prag raportare cash 50.000 RON)
        # Prag 2: 4.000 - 4.999 EUR (prag 5.000 EUR)
        suspect_items = []
        for r in records:
            amt = abs(r.get("amount") or 0.0)
            curr = (r.get("currency") or "RON").upper()
            is_smurfing = False
            if curr in ["RON", "LEI"] and 40000.0 <= amt < 50000.0:
                is_smurfing = True
            elif curr in ["EUR", "USD"] and 4000.0 <= amt < 5000.0:
                is_smurfing = True

            if is_smurfing:
                suspect_items.append({
                    "id": r.get("id"),
                    "filename": r.get("doc_filename"),
                    "amount": amt,
                    "currency": curr,
                    "date": r.get("transaction_date"),
                    "counterparty": r.get("cui_destination") or r.get("iban_destination") or r.get("description")
                })

        return {
            "count": len(suspect_items),
            "risk_flag": len(suspect_items) >= 2,
            "details": suspect_items
        }

    def _check_duplicates(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        seen = defaultdict(list)
        duplicates = []

        for r in records:
            amt = round(abs(r.get("amount") or 0.0), 2)
            if amt > 0.0:
                doc_num = (r.get("doc_number") or "").strip()
                dest = (r.get("cui_destination") or r.get("iban_destination") or "").strip()
                key = f"{amt}_{doc_num}" if doc_num else f"{amt}_{dest}" if dest else None
                if key:
                    seen[key].append(r)

        for key, group in seen.items():
            if len(group) > 1:
                duplicates.append({
                    "signature": key,
                    "count": len(group),
                    "amount": abs(group[0].get("amount") or 0.0),
                    "instances": [{
                        "id": x.get("id"),
                        "filename": x.get("doc_filename"),
                        "doc_number": x.get("doc_number"),
                        "date": x.get("transaction_date")
                    } for x in group]
                })

        return {
            "count": len(duplicates),
            "risk_flag": len(duplicates) > 0,
            "groups": duplicates
        }

    def _check_weekends(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        weekend_ops = []
        date_formats = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"]

        for r in records:
            raw_date = (r.get("transaction_date") or "").strip()
            if not raw_date: continue
            
            clean_date = raw_date[:10]
            dt = None
            for fmt in date_formats:
                try:
                    dt = datetime.strptime(clean_date, fmt)
                    break
                except ValueError:
                    continue

            if dt and dt.weekday() in [5, 6]: # Sâmbătă (5) sau Duminică (6)
                weekend_ops.append({
                    "id": r.get("id"),
                    "filename": r.get("doc_filename"),
                    "date": raw_date,
                    "day": "Sâmbătă" if dt.weekday() == 5 else "Duminică",
                    "amount": r.get("amount"),
                    "currency": r.get("currency")
                })

        return {
            "count": len(weekend_ops),
            "risk_flag": len(weekend_ops) > 0,
            "operations": weekend_ops
        }

    def _check_round_numbers(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        round_items = []
        eligible = 0

        for r in records:
            amt = abs(r.get("amount") or 0.0)
            if amt >= 1000.0:
                eligible += 1
                if amt % 1000.0 == 0:
                    round_items.append({
                        "id": r.get("id"),
                        "filename": r.get("doc_filename"),
                        "amount": amt,
                        "currency": r.get("currency")
                    })

        ratio = round(len(round_items) / eligible, 3) if eligible > 0 else 0.0
        # Mai mult de 30% numere rotunde mari reprezintă un indicator puternic de plăți convenite / fictive
        risk_flag = eligible >= 5 and ratio >= 0.30

        return {
            "eligible_count": eligible,
            "round_count": len(round_items),
            "round_ratio": ratio,
            "risk_flag": risk_flag,
            "details": round_items[:10]
        }

anomaly_service = FinancialAnomalyService()
