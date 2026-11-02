"""
Audit Log Repository
Manages security and activity audit trail records in audit_logs table.
Includes DB persistence with in-memory fallback for offline testing/development.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
import hashlib
import hmac

from config.settings import settings
from database.connection import get_connection
from utils.logger import get_logger

logger = get_logger("repositories.audit_repository")

GENESIS_HASH = "0" * 64
AUDIT_SECRET = getattr(settings, "AUDIT_CHAIN_SECRET", "faculty_erp_audit_chain_hmac_secret_2026")


class AuditRepository:
    """Repository recording and querying system and security audit entries."""

    @classmethod
    def compute_entry_hash(cls, entry: Dict[str, Any], prev_hash: str) -> str:
        """Computes cryptographic HMAC-SHA256 for an audit entry chained with previous entry's hash."""
        ts = entry.get("timestamp")
        if isinstance(ts, datetime):
            ts = ts.strftime("%Y-%m-%d %H:%M:%S")
        payload = (
            f"{entry.get('id')}|{entry.get('user_id')}|{entry.get('action')}|"
            f"{entry.get('entity_type')}|{entry.get('entity_id')}|{entry.get('details')}|"
            f"{entry.get('ip_address')}|{ts}|{prev_hash}"
        )
        return hmac.new(AUDIT_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def __init__(self):
        self._in_memory_logs: List[Dict[str, Any]] = [
            {
                "id": 1,
                "user_id": 1,
                "username": "admin",
                "action": "SYSTEM_INIT",
                "entity_type": "SYSTEM",
                "entity_id": "SYS001",
                "details": "ERP System initialized successfully.",
                "ip_address": "127.0.0.1",
                "timestamp": "2026-10-01 09:00:00",
            },
            {
                "id": 2,
                "user_id": 1,
                "username": "admin",
                "action": "LOGIN_SUCCESS",
                "entity_type": "USER",
                "entity_id": "1",
                "details": "User 'admin' logged in successfully with role 'ADMIN'.",
                "ip_address": "127.0.0.1",
                "timestamp": "2026-10-01 09:05:00",
            },
            {
                "id": 3,
                "user_id": 2,
                "username": "hod_mca",
                "action": "LEAVE_APPROVAL",
                "entity_type": "LEAVE_APPLICATION",
                "entity_id": "LV-101",
                "details": "Leave application LV-101 approved by HOD.",
                "ip_address": "127.0.0.1",
                "timestamp": "2026-10-02 10:15:00",
            },
            {
                "id": 4,
                "user_id": 3,
                "username": "fac_rahul",
                "action": "LEAVE_SUBMISSION",
                "entity_type": "LEAVE_APPLICATION",
                "entity_id": "LV-102",
                "details": "Submitted leave application for Medical Leave (2 days).",
                "ip_address": "127.0.0.1",
                "timestamp": "2026-10-03 11:30:00",
            },
        ]
        self._next_id = 5

        # Initialize cryptographic hash chain on seed entries
        curr_prev = GENESIS_HASH
        for entry in self._in_memory_logs:
            entry["prev_hash"] = curr_prev
            entry["entry_hash"] = self.compute_entry_hash(entry, curr_prev)
            curr_prev = entry["entry_hash"]

    def log_event(
        self,
        user_id: Optional[int],
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = "127.0.0.1",
    ):
        """
        Inserts a structured security audit record using parameterized query with hash-chaining.
        Also records entry in in-memory fallback list.
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[AUDIT LOG] UserID: {user_id} | Action: {action} | Entity: {entity_type} ({entity_id}) | Details: {details}"
        logger.info(log_msg)

        # Hash-chain linkage with previous entry
        prev_hash = self._in_memory_logs[-1]["entry_hash"] if self._in_memory_logs else GENESIS_HASH

        mem_entry = {
            "id": self._next_id,
            "user_id": user_id,
            "username": f"user_{user_id}" if user_id else "SYSTEM",
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "details": details,
            "ip_address": ip_address,
            "timestamp": now_str,
            "prev_hash": prev_hash,
        }
        mem_entry["entry_hash"] = self.compute_entry_hash(mem_entry, prev_hash)

        self._in_memory_logs.append(mem_entry)
        self._next_id += 1

        query = """
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, ip_address, prev_hash, entry_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                query,
                (user_id, action, entity_type, entity_id, details, ip_address, prev_hash, mem_entry["entry_hash"]),
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as exc:
            logger.debug(f"DB audit log entry skipped (DB offline): {exc}")

    def get_audit_logs(
        self,
        limit: int = 200,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        search_term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetches audit logs with filtering by user, action, entity type, and text search.
        Falls back to in-memory audit logs if DB is offline.
        """
        query = """
            SELECT a.id, a.user_id, u.username, a.action, a.entity_type, a.entity_id,
                   a.details, a.ip_address, a.timestamp, a.prev_hash, a.entry_hash
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE 1=1
        """
        params: List[Any] = []

        if user_id is not None:
            query += " AND a.user_id = %s"
            params.append(user_id)
        if action and action.upper() != "ALL":
            query += " AND a.action = %s"
            params.append(action)
        if entity_type and entity_type.upper() != "ALL":
            query += " AND a.entity_type = %s"
            params.append(entity_type)
        if search_term:
            query += " AND (a.details LIKE %s OR a.entity_id LIKE %s OR u.username LIKE %s)"
            pattern = f"%{search_term}%"
            params.extend([pattern, pattern, pattern])

        query += " ORDER BY a.timestamp DESC LIMIT %s"
        params.append(limit)

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            if rows:
                formatted_rows = []
                for r in rows:
                    row_dict = dict(r)
                    if isinstance(row_dict.get("timestamp"), datetime):
                        row_dict["timestamp"] = row_dict["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                    formatted_rows.append(row_dict)
                return formatted_rows
        except Exception as exc:
            logger.debug(f"DB fetch audit logs failed, fallback to memory: {exc}")

        # In-memory filtering fallback
        results = list(self._in_memory_logs)

        if user_id is not None:
            results = [r for r in results if r.get("user_id") == user_id]
        if action and action.upper() != "ALL":
            results = [r for r in results if r.get("action") == action]
        if entity_type and entity_type.upper() != "ALL":
            results = [r for r in results if r.get("entity_type") == entity_type]
        if search_term:
            st = search_term.lower()
            results = [
                r for r in results
                if st in (r.get("details") or "").lower()
                or st in (r.get("entity_id") or "").lower()
                or st in (r.get("username") or "").lower()
            ]

        results.sort(key=lambda x: str(x.get("timestamp")), reverse=True)
        return results[:limit]

    def verify_chain_integrity(self, logs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Cryptographically verifies the audit log hash chain.
        Detects unauthorized insertions, deletions, modifications, and reordering.
        """
        chain = logs if logs is not None else list(self._in_memory_logs)
        if not chain:
            return {"is_valid": True, "total_verified": 0, "head_hash": GENESIS_HASH}

        # Verify in strictly chronological / ascending ID order
        chain_sorted = sorted(chain, key=lambda x: int(x.get("id", 0)))

        expected_prev = GENESIS_HASH
        for idx, entry in enumerate(chain_sorted):
            actual_prev = entry.get("prev_hash")
            if actual_prev != expected_prev:
                return {
                    "is_valid": False,
                    "tampered_index": idx,
                    "tampered_id": entry.get("id"),
                    "reason": f"PREVIOUS_HASH_MISMATCH: expected {expected_prev[:12]}..., found {str(actual_prev)[:12]}...",
                }

            recomputed_hash = self.compute_entry_hash(entry, expected_prev)
            actual_hash = entry.get("entry_hash")
            if not actual_hash or not hmac.compare_digest(actual_hash, recomputed_hash):
                return {
                    "is_valid": False,
                    "tampered_index": idx,
                    "tampered_id": entry.get("id"),
                    "reason": f"PAYLOAD_HASH_MISMATCH: tampering detected on audit row ID {entry.get('id')}",
                }
            expected_prev = actual_hash

        return {
            "is_valid": True,
            "total_verified": len(chain_sorted),
            "head_hash": expected_prev,
        }


audit_repository = AuditRepository()
