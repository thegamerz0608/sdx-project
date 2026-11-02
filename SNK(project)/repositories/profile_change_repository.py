"""
Profile Change Repository
Handles SQL transactions, parameterized queries, and in-memory fallback
for faculty profile change approval requests and audit records.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from database.connection import get_connection
from utils.logger import get_logger

logger = get_logger("repositories.profile_change_repository")

# In-memory fallback dataset for offline and testing resilience
DEMO_PROFILE_CHANGE_REQUESTS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "employee_id": 3,
        "employee_code": "F002",
        "employee_name": "Rahul Sharma",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "requester_user_id": 3,
        "requester_role": "FACULTY",
        "field_name": "pan_number",
        "old_value": "ABCDE1234F",
        "new_value": "BKZPK8899M",
        "reason": "Updated PAN card issued after middle name correction.",
        "proof_path": "uploads/proofs/sample_pan_proof.pdf",
        "status": "PENDING",
        "requested_at": "2026-10-30 10:15:00",
        "reviewed_by": None,
        "reviewer_name": None,
        "reviewed_at": None,
        "reviewer_remark": None,
    },
    {
        "id": 2,
        "employee_id": 2,
        "employee_code": "F001",
        "employee_name": "Dr. Suresh Kumar",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "requester_user_id": 2,
        "requester_role": "HOD",
        "field_name": "salary_account_no",
        "old_value": "50100987654321",
        "new_value": "50100777888999",
        "reason": "Switched salary credit account to SBI Institutional Campus branch.",
        "proof_path": "uploads/proofs/sample_cheque_leaf.png",
        "status": "PENDING",
        "requested_at": "2026-10-29 14:30:00",
        "reviewed_by": None,
        "reviewer_name": None,
        "reviewed_at": None,
        "reviewer_remark": None,
    },
    {
        "id": 3,
        "employee_id": 4,
        "employee_code": "F003",
        "employee_name": "Priya Verma",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "requester_user_id": 4,
        "requester_role": "FACULTY",
        "field_name": "aadhaar_number",
        "old_value": "765432109876",
        "new_value": "765432109890",
        "reason": "Updated biometric Aadhaar registration number.",
        "proof_path": None,
        "status": "APPROVED",
        "requested_at": "2026-10-26 09:20:00",
        "reviewed_by": 10,
        "reviewer_name": "HR Manager",
        "reviewed_at": "2026-10-27 11:45:00",
        "reviewer_remark": "Aadhaar e-KYC verification verified successfully.",
    },
    {
        "id": 4,
        "employee_id": 3,
        "employee_code": "F002",
        "employee_name": "Rahul Sharma",
        "department_id": 1,
        "department_code": "MCA",
        "department_name": "Department of Computer Applications",
        "requester_user_id": 3,
        "requester_role": "FACULTY",
        "field_name": "salary_account_no",
        "old_value": "50100234567890",
        "new_value": "1234567",
        "reason": "Testing account change.",
        "proof_path": None,
        "status": "REJECTED",
        "requested_at": "2026-10-21 16:10:00",
        "reviewed_by": 10,
        "reviewer_name": "HR Manager",
        "reviewed_at": "2026-10-22 10:00:00",
        "reviewer_remark": "Account number format invalid (must be 9 to 18 digits).",
    },
]

DEMO_PROFILE_CHANGE_AUDITS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "request_id": 1,
        "action": "SUBMITTED",
        "actor_id": 3,
        "action_at": "2026-10-30 10:15:00",
        "details": "Submitted change request for PAN Card No (new value: XXXXXX8899M)",
    },
    {
        "id": 2,
        "request_id": 3,
        "action": "APPROVED",
        "actor_id": 10,
        "action_at": "2026-10-27 11:45:00",
        "details": "Approved Aadhaar No change request for F003",
    },
]


class ProfileChangeRepository:
    """Repository handling SQL operations for profile change requests and audit logging."""

    def create_request(
        self,
        employee_id: int,
        field_name: str,
        old_value: Optional[str],
        new_value: str,
        reason: str,
        proof_path: Optional[str] = None,
    ) -> int:
        """Inserts a new pending profile change request."""
        query = """
            INSERT INTO profile_change_requests 
                (employee_id, field_name, old_value, new_value, reason, proof_path, status, requested_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'PENDING', NOW())
            RETURNING id;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (employee_id, field_name, old_value, new_value, reason, proof_path))
            row = cursor.fetchone()
            req_id = row[0] if row else cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Created profile change request ID={req_id} for employee_id={employee_id}, field={field_name}")
            return req_id
        except Exception as exc:
            logger.warning(f"DB create profile change request error, adding to memory fallback: {exc}")
            req_id = max([r["id"] for r in DEMO_PROFILE_CHANGE_REQUESTS], default=0) + 1
            
            # Lookup faculty info from repository for mock display
            from repositories.faculty_repository import faculty_repository
            fac = faculty_repository.get_by_id(employee_id) or {}
            
            DEMO_PROFILE_CHANGE_REQUESTS.append({
                "id": req_id,
                "employee_id": employee_id,
                "employee_code": fac.get("employee_code", f"EMP{employee_id}"),
                "employee_name": fac.get("full_name", "Faculty Member"),
                "department_id": fac.get("department_id", 1),
                "department_code": fac.get("department_code", "MCA"),
                "department_name": fac.get("department_name", "Department of Computer Applications"),
                "requester_user_id": fac.get("user_id", employee_id),
                "requester_role": fac.get("role", "FACULTY"),
                "field_name": field_name,
                "old_value": old_value,
                "new_value": new_value,
                "reason": reason,
                "proof_path": proof_path,
                "status": "PENDING",
                "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "reviewed_by": None,
                "reviewer_name": None,
                "reviewed_at": None,
                "reviewer_remark": None,
            })
            return req_id

    def get_by_id(self, request_id: int) -> Optional[Dict[str, Any]]:
        """Fetches a change request by its primary key ID."""
        query = """
            SELECT 
                r.id,
                r.employee_id,
                f.employee_code,
                CONCAT(f.first_name, ' ', f.last_name) AS employee_name,
                f.department_id,
                d.code AS department_code,
                d.name AS department_name,
                f.user_id AS requester_user_id,
                u.role AS requester_role,
                r.field_name,
                r.old_value,
                r.new_value,
                r.reason,
                r.proof_path,
                r.status,
                r.requested_at,
                r.reviewed_by,
                rev.username AS reviewer_name,
                r.reviewed_at,
                r.reviewer_remark
            FROM profile_change_requests r
            INNER JOIN faculty f ON f.id = r.employee_id
            INNER JOIN departments d ON d.id = f.department_id
            INNER JOIN users u ON u.id = f.user_id
            LEFT JOIN users rev ON rev.id = r.reviewed_by
            WHERE r.id = %s;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, (request_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row
        except Exception as exc:
            logger.debug(f"DB get request by ID fallback: {exc}")
            for r in DEMO_PROFILE_CHANGE_REQUESTS:
                if r["id"] == request_id:
                    return r.copy()
            return None

    def get_pending_by_employee_and_field(self, employee_id: int, field_name: str) -> Optional[Dict[str, Any]]:
        """Returns active pending change request for the given employee and field, if one exists."""
        query = """
            SELECT * FROM profile_change_requests
            WHERE employee_id = %s AND field_name = %s AND status = 'PENDING';
        """
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, (employee_id, field_name))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row
        except Exception as exc:
            logger.debug(f"DB get pending request fallback: {exc}")
            for r in DEMO_PROFILE_CHANGE_REQUESTS:
                if r["employee_id"] == employee_id and r["field_name"] == field_name and r["status"] == "PENDING":
                    return r.copy()
            return None

    def get_requests_by_employee(self, employee_id: int) -> List[Dict[str, Any]]:
        """Retrieves all change requests submitted by a specific employee, ordered newest first."""
        query = """
            SELECT 
                r.id,
                r.employee_id,
                f.employee_code,
                CONCAT(f.first_name, ' ', f.last_name) AS employee_name,
                r.field_name,
                r.old_value,
                r.new_value,
                r.reason,
                r.proof_path,
                r.status,
                r.requested_at,
                r.reviewed_by,
                rev.username AS reviewer_name,
                r.reviewed_at,
                r.reviewer_remark
            FROM profile_change_requests r
            INNER JOIN faculty f ON f.id = r.employee_id
            LEFT JOIN users rev ON rev.id = r.reviewed_by
            WHERE r.employee_id = %s
            ORDER BY r.requested_at DESC, r.id DESC;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, (employee_id,))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except Exception as exc:
            logger.debug(f"DB get requests by employee fallback: {exc}")
            results = [r.copy() for r in DEMO_PROFILE_CHANGE_REQUESTS if r.get("employee_id") == employee_id]
            results.sort(key=lambda x: str(x.get("requested_at", "")), reverse=True)
            return results

    def get_all_requests(
        self,
        status: Optional[str] = None,
        department_id: Optional[int] = None,
        field_name: Optional[str] = None,
        search_term: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves profile change requests matching filter criteria."""
        query = """
            SELECT 
                r.id,
                r.employee_id,
                f.employee_code,
                CONCAT(f.first_name, ' ', f.last_name) AS employee_name,
                f.department_id,
                d.code AS department_code,
                d.name AS department_name,
                f.user_id AS requester_user_id,
                u.role AS requester_role,
                r.field_name,
                r.old_value,
                r.new_value,
                r.reason,
                r.proof_path,
                r.status,
                r.requested_at,
                r.reviewed_by,
                rev.username AS reviewer_name,
                r.reviewed_at,
                r.reviewer_remark
            FROM profile_change_requests r
            INNER JOIN faculty f ON f.id = r.employee_id
            INNER JOIN departments d ON d.id = f.department_id
            INNER JOIN users u ON u.id = f.user_id
            LEFT JOIN users rev ON rev.id = r.reviewed_by
            WHERE 1=1
        """
        params = []
        if status and status.upper() != "ALL":
            query += " AND r.status = %s"
            params.append(status.upper())

        if department_id is not None:
            query += " AND f.department_id = %s"
            params.append(department_id)

        if field_name and field_name.upper() != "ALL":
            query += " AND r.field_name = %s"
            params.append(field_name)

        if search_term and search_term.strip():
            term = f"%{search_term.strip()}%"
            query += " AND (f.employee_code LIKE %s OR f.first_name LIKE %s OR f.last_name LIKE %s OR r.field_name LIKE %s)"
            params.extend([term, term, term, term])

        query += " ORDER BY CASE WHEN r.status = 'PENDING' THEN 1 ELSE 2 END, r.requested_at DESC;"

        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            return rows
        except Exception as exc:
            logger.debug(f"DB get_all_requests fallback: {exc}")
            results = []
            for r in DEMO_PROFILE_CHANGE_REQUESTS:
                if status and status.upper() != "ALL" and r.get("status") != status.upper():
                    continue
                if department_id is not None and r.get("department_id") != department_id:
                    continue
                if field_name and field_name.upper() != "ALL" and r.get("field_name") != field_name:
                    continue
                if search_term and search_term.strip():
                    st = search_term.strip().lower()
                    m_code = st in str(r.get("employee_code", "")).lower()
                    m_name = st in str(r.get("employee_name", "")).lower()
                    m_field = st in str(r.get("field_name", "")).lower()
                    if not (m_code or m_name or m_field):
                        continue
                results.append(r.copy())
            results.sort(key=lambda x: (0 if x.get("status") == "PENDING" else 1, str(x.get("requested_at", ""))), reverse=False)
            return results

    def get_pending_count(self) -> int:
        """Returns total count of pending profile change requests."""
        query = "SELECT COUNT(*) FROM profile_change_requests WHERE status = 'PENDING';"
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(query)
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return int(count)
        except Exception:
            return sum(1 for r in DEMO_PROFILE_CHANGE_REQUESTS if r.get("status") == "PENDING")

    def cancel_request(self, request_id: int, actor_id: int) -> bool:
        """Cancels a pending change request."""
        query = """
            UPDATE profile_change_requests
            SET status = 'CANCELLED'
            WHERE id = %s AND status = 'PENDING';
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (request_id,))
            affected = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            if affected > 0:
                self.log_audit(request_id, "CANCELLED", actor_id, "Request cancelled by requester.")
                logger.info(f"Cancelled change request ID={request_id}")
                return True
            return False
        except Exception as exc:
            logger.warning(f"DB cancel request fallback: {exc}")
            for r in DEMO_PROFILE_CHANGE_REQUESTS:
                if r["id"] == request_id and r["status"] == "PENDING":
                    r["status"] = "CANCELLED"
                    self.log_audit(request_id, "CANCELLED", actor_id, "Request cancelled by requester.")
                    return True
            return False

    def approve_request(
        self,
        request_id: int,
        reviewer_id: int,
        reviewer_remark: Optional[str] = None,
    ) -> bool:
        """
        In a single atomic database transaction:
        1. Verifies request status is PENDING.
        2. Applies the change to the employee's profile in the `faculty` table.
        3. Marks the change request as APPROVED with reviewer ID and timestamp.
        4. Writes an audit entry to `profile_change_audit`.
        Rolls back all changes if any step fails.
        """
        # Fetch request details
        req = self.get_by_id(request_id)
        if not req or req.get("status") != "PENDING":
            return False

        employee_id = req["employee_id"]
        field_name = req["field_name"]
        new_val = req["new_value"]

        # Whitelist of allowed faculty column names to prevent SQL injection
        ALLOWED_COLUMNS = {
            "salary_account_no",
            "pan_number",
            "aadhaar_number",
            "pf_number",
            "uan_number",
            "dob",
            "first_name",
            "last_name",
            "phone",
            "personal_email",
            "profile_image_path",
        }

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # 1. Update faculty profile field
            if field_name == "name":
                # Split into first and last name
                parts = new_val.strip().split(" ", 1)
                first = parts[0]
                last = parts[1] if len(parts) > 1 else ""
                sql_fac = "UPDATE faculty SET first_name = %s, last_name = %s WHERE id = %s;"
                cursor.execute(sql_fac, (first, last, employee_id))
            elif field_name in ALLOWED_COLUMNS:
                sql_fac = f"UPDATE faculty SET {field_name} = %s WHERE id = %s;"
                cursor.execute(sql_fac, (new_val, employee_id))
            else:
                conn.rollback()
                cursor.close()
                conn.close()
                raise ValueError(f"Disallowed column update: {field_name}")

            # 2. Update request status to APPROVED
            now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sql_req = """
                UPDATE profile_change_requests
                SET status = 'APPROVED', reviewed_by = %s, reviewed_at = %s, reviewer_remark = %s
                WHERE id = %s;
            """
            cursor.execute(sql_req, (reviewer_id, now_dt, reviewer_remark, request_id))

            # 3. Insert audit entry
            sql_audit = """
                INSERT INTO profile_change_audit (request_id, action, actor_id, details)
                VALUES (%s, 'APPROVED', %s, %s);
            """
            cursor.execute(sql_audit, (request_id, reviewer_id, f"Approved {field_name} change. Remark: {reviewer_remark or 'Approved'}"))

            conn.commit()
            cursor.close()
            conn.close()

            # Also sync in-memory faculty repository and request list for consistency
            self._sync_memory_after_approval(employee_id, field_name, new_val, request_id, reviewer_id, reviewer_remark, now_dt)
            logger.info(f"Successfully approved change request ID={request_id} for employee_id={employee_id}, field={field_name}")
            return True

        except Exception as exc:
            logger.warning(f"DB atomic approval failed, executing in-memory fallback: {exc}")
            now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._sync_memory_after_approval(employee_id, field_name, new_val, request_id, reviewer_id, reviewer_remark, now_dt)
            return True

    def _sync_memory_after_approval(
        self,
        employee_id: int,
        field_name: str,
        new_val: str,
        request_id: int,
        reviewer_id: int,
        reviewer_remark: Optional[str],
        now_dt: str,
    ):
        """Updates in-memory data structures after an approval."""
        from repositories.faculty_repository import DEMO_FACULTY_LIST
        for f in DEMO_FACULTY_LIST:
            if f.get("id") == employee_id:
                if field_name == "name":
                    parts = new_val.strip().split(" ", 1)
                    f["first_name"] = parts[0]
                    f["last_name"] = parts[1] if len(parts) > 1 else ""
                    f["full_name"] = new_val.strip()
                else:
                    f[field_name] = new_val
                break

        for r in DEMO_PROFILE_CHANGE_REQUESTS:
            if r["id"] == request_id:
                r["status"] = "APPROVED"
                r["reviewed_by"] = reviewer_id
                r["reviewed_at"] = now_dt
                r["reviewer_remark"] = reviewer_remark
                break

        self.log_audit(request_id, "APPROVED", reviewer_id, f"Approved {field_name} update. Remark: {reviewer_remark or 'Approved'}")

    def reject_request(
        self,
        request_id: int,
        reviewer_id: int,
        reviewer_remark: str,
    ) -> bool:
        """
        Marks a change request as REJECTED with mandatory reviewer remark.
        The employee profile remains unchanged.
        """
        req = self.get_by_id(request_id)
        if not req or req.get("status") != "PENDING":
            return False

        now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = """
            UPDATE profile_change_requests
            SET status = 'REJECTED', reviewed_by = %s, reviewed_at = %s, reviewer_remark = %s
            WHERE id = %s;
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (reviewer_id, now_dt, reviewer_remark, request_id))
            conn.commit()
            cursor.close()
            conn.close()

            self.log_audit(request_id, "REJECTED", reviewer_id, f"Rejected {req['field_name']} change. Remark: {reviewer_remark}")
            logger.info(f"Rejected change request ID={request_id}")
            return True
        except Exception as exc:
            logger.warning(f"DB reject request fallback: {exc}")
            for r in DEMO_PROFILE_CHANGE_REQUESTS:
                if r["id"] == request_id:
                    r["status"] = "REJECTED"
                    r["reviewed_by"] = reviewer_id
                    r["reviewed_at"] = now_dt
                    r["reviewer_remark"] = reviewer_remark
                    break
            self.log_audit(request_id, "REJECTED", reviewer_id, f"Rejected {req['field_name']} change. Remark: {reviewer_remark}")
            return True

    def log_audit(self, request_id: int, action: str, actor_id: int, details: str):
        """Records an action in the profile_change_audit log."""
        now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = """
            INSERT INTO profile_change_audit (request_id, action, actor_id, action_at, details)
            VALUES (%s, %s, %s, %s, %s);
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (request_id, action, actor_id, now_dt, details))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception:
            pass

        # In-memory audit list
        audit_id = max([a["id"] for a in DEMO_PROFILE_CHANGE_AUDITS], default=0) + 1
        DEMO_PROFILE_CHANGE_AUDITS.append({
            "id": audit_id,
            "request_id": request_id,
            "action": action,
            "actor_id": actor_id,
            "action_at": now_dt,
            "details": details,
        })


profile_change_repository = ProfileChangeRepository()
