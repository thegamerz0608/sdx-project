# Enterprise Security Architecture & Threat Model (Phase 2)
**Project Title:** AI-Enabled Faculty Attendance, Leave and Substitute Management ERP  
**Security Specification Version:** 3.1.0  
**Compliance Standard:** OWASP Top 10 (2021/2024), RFC 7914 (Scrypt), RFC 7519 (JWT), India DPDP Act 2023  
**Target Environment:** Institutional Windows Desktop Workstations + FastAPI Web/Mobile LAN Gateways  

---

## 1. Executive Summary & Security Posture

The **Faculty Attendance, Leave and Substitute Management ERP** operates within an educational institution managing sensitive faculty personal identifiable information (PII), payroll-linked attendance records, statutory leave balances, and biometric authentication assertions.

This specification documents the multi-layered defense-in-depth architecture implemented across Phase 2, including memory-hard password hashing with transparent rehash, dual-token JWT sessions with revocation, cryptographic audit log hash chaining, HMAC backup signing, TOTP-style rotating QR kiosk check-in, and statutory alignment with India's **Digital Personal Data Protection (DPDP) Act 2023**.

---

## 2. Threat Model & Adversary Classifications

| Threat Identifier | Adversary Profile | Threat Vector | Implemented Mitigation |
|---|---|---|---|
| **T-01: Credential Brute-Forcing** | External attacker or curious student | High-frequency password guessing on `/staff-login` or `/admin-login` | Sliding-window rate limiting (30 attempts/min) + Scrypt memory-hard hashing ($N=16384$). |
| **T-02: Offline DB Hash Cracking** | Malicious insider with read-only DB dump | GPU/ASIC offline dictionary attack against stored hashes | Migration to memory-hard Scrypt ($N=16384, r=8, p=1$); 16-byte cryptographically secure random salts. |
| **T-03: Remote / Proxy Punching** | Faculty member attempting off-campus check-in | Photographing static QR code or bookmarking URL to punch from home | Dynamic TOTP-style rotating QR code (30s window) + single-use replay protection cache. |
| **T-04: Audit Trail Tampering** | Privileged admin covering up unauthorized leave modification | Direct SQL `UPDATE` or `DELETE` on `audit_logs` table | Cryptographic HMAC-SHA256 hash chaining + SQL `REVOKE UPDATE, DELETE` privilege restrictions. |
| **T-05: Backup Corruption / Injection** | Attacker tampering with SQL/JSON dumps in backup archive | Altering leave balances or injecting admin users into backup `.zip` | HMAC-SHA256 signature on `manifest.json` verified before restore + AES-256-GCM encryption. |
| **T-06: Cross-Site Request Forgery (CSRF)** | Malicious third-party website | Forcing authenticated faculty browser to submit leave application | Double-submit anti-CSRF token verification (`X-CSRF-Token`) + `SameSite="lax"` cookie flags. |
| **T-07: Session Hijacking & Replay** | Man-in-the-Middle on campus LAN | Intercepting unexpired JWT bearer tokens | Short-lived access tokens (30 min) + rotating refresh tokens + active token revocation blocklist (`REVOKED_TOKENS`). |
| **T-08: Biometric Privacy Violation** | Unauthorized capture of biometric templates | Intercepting or storing faculty fingerprint minutiae | WebAuthn/FIDO2 client-side biometrics; zero raw biometric template storage on server (DPDP Act 2023). |

---

## 3. Password Security: Memory-Hard Scrypt & Transparent Rehash

### 3.1 Scrypt Parameterization (RFC 7914 / OWASP)
The system utilizes standard library `hashlib.scrypt` with parameters specifically tuned to resist ASIC and GPU hardware acceleration:
- **$N = 16384$** (CPU/memory cost factor: requires 16 MiB RAM per hash evaluation)
- **$r = 8$** (Block size parameter)
- **$p = 1$** (Parallelization parameter)
- **Salt:** 16 bytes of cryptographically secure randomness generated via `os.urandom(16)`.
- **Hash Storage Format:** `scrypt$16384$8$1${salt_hex}${key_hex}`

### 3.2 Transparent In-Place Rehash Mechanism
To upgrade legacy systems without requiring a forced, disruptive password reset for all employees:
1. When a user submits credentials, `verify_password(password, stored_hash)` evaluates the hash.
2. The verification engine supports Scrypt, legacy PBKDF2-HMAC-SHA256 (`salt$hash`), and legacy SHA-256 fallback.
3. If verification succeeds and `needs_rehash(stored_hash)` evaluates to `True`, the service immediately computes a new Scrypt hash and executes an atomic update in the repository:
   ```sql
   UPDATE users SET password_hash = %s WHERE id = %s;
   ```
4. Subsequent logins execute entirely on the upgraded Scrypt hash.

---

## 4. Web Gateway & Session Hardening

### 4.1 Cookie Security Flags
All authentication and session cookies issued by `services/web_portal_service.py` (`cms_token`, `admin_token`, `cms_session`) enforce strict browser isolation:
- `HttpOnly = True`: Prevents client-side JavaScript access via `document.cookie`, mitigating XSS exfiltration.
- `SameSite = "lax"`: Prevents CSRF token transmission during cross-site sub-requests while enabling seamless top-level navigation.
- `Secure = True`: Enforced when `COOKIE_SECURE=true` in `.env` (mandatory for HTTPS production deployments).
- `Max-Age`: Bound to session lifespans.

### 4.2 Dual Tokens & Immediate Session Revocation
- **Access Tokens:** Short-lived JWTs (30 minutes) carrying minimal authorization claims.
- **Refresh Tokens:** Long-lived rotating tokens (7 days) stored securely to negotiate fresh access credentials.
- **Revocation Blocklist:** When a user logs out via `/staff-logout` or `/admin-logout`, active tokens are submitted to the `REVOKED_TOKENS` blocklist. Subsequent requests presenting revoked tokens are rejected with HTTP 401 Unauthorized.

### 4.3 Double-Submit Anti-CSRF Protection
State-changing POST endpoints (such as `/api/leaves/apply`, `/api/profile/update`, and marks entry) require an anti-CSRF token:
$$\text{CSRF Token} = \text{SessionID} \parallel \text{HMAC-SHA256}(\text{"csrf:"} \parallel \text{SessionID}, \mathcal{K}_{\text{csrf}})$$
The client sends the token via the `X-CSRF-Token` header or form payload. Requests with mismatched or absent CSRF tokens are rejected.

### 4.4 Sliding-Window Rate Limiting (`utils/rate_limiter.py`)
Authentication and punch routes enforce an in-memory sliding window algorithm:
- `/staff-login` & `/admin-login`: Max 30 attempts per 60-second window per IP.
- `/api/punch`: Max 60 attempts per 60-second window per IP.
Exceeding the threshold returns HTTP 429 Too Many Requests with a `Retry-After` header.

### 4.5 Mandatory HTTP Security Headers
Every HTTP response emitted by the FastAPI bridge is injected with enterprise security headers:
```http
Content-Security-Policy: default-src 'self' 'unsafe-inline' data:; frame-ancestors 'none';
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

---

## 5. Cryptographic Hash-Chained Audit Trail

### 5.1 Merkle/Blockchain Hash Chaining Architecture
In standard relational databases, audit logs stored in plain SQL tables can be altered or deleted by malicious database administrators. To guarantee **data non-repudiation and tamper-evidence**, each audit log record is cryptographically linked to its predecessor:

$$\text{Hash}_0 = \text{"0"}^{64} \quad (\text{Genesis Hash})$$
$$\text{Hash}_i = \text{HMAC-SHA256}\Big(\text{ID}_i \parallel \text{UserID}_i \parallel \text{Action}_i \parallel \text{EntityType}_i \parallel \text{EntityID}_i \parallel \text{Details}_i \parallel \text{Timestamp}_i \parallel \text{Hash}_{i-1}, \mathcal{K}_{\text{audit}}\Big)$$

Each row stores:
- `prev_hash`: The `entry_hash` of the immediately preceding record ($i-1$).
- `entry_hash`: The cryptographic HMAC calculated over the record's payload and `prev_hash`.

### 5.2 Automated Tamper Verification (`verify_chain_integrity`)
The `AuditRepository.verify_chain_integrity()` function iterates chronologically from Genesis:
1. Recomputes $\text{Hash}_i$ for every entry using the known secret key.
2. Verifies that `entry[i].prev_hash == entry[i-1].entry_hash`.
3. Verifies that `entry[i].entry_hash == recomputed_hash`.
4. If an attacker modifies an old row (e.g. changing an approved leave or clearing an infraction), the hash chain breaks at that exact index, returning:
   ```json
   {
     "is_valid": false,
     "tampered_id": 2,
     "reason": "PAYLOAD_HASH_MISMATCH: tampering detected on audit row ID 2"
   }
   ```

### 5.3 Database Privilege Hardening (SQL Defense-in-Depth)
To prevent unauthorized deletion even by compromised application credentials, database administrators must revoke write-alteration privileges on the `audit_logs` table:
```sql
-- Grant INSERT and SELECT privileges only to the application service user
GRANT INSERT, SELECT ON faculty_erp_db.audit_logs TO 'faculty_app'@'localhost';

-- Explicitly revoke UPDATE and DELETE to enforce append-only immutability
REVOKE UPDATE, DELETE ON faculty_erp_db.audit_logs FROM 'faculty_app'@'localhost';
FLUSH PRIVILEGES;
```

---

## 6. Backup Cryptographic Integrity & AES-256-GCM Encryption

### 6.1 Cryptographic Manifest Signing
Backups generated by `services/backup_service.py` contain:
1. Table SQL and JSON dumps with individual file SHA-256 checksums in `manifest.json`.
2. An institutional HMAC-SHA256 signature calculated over canonical JSON:
   $$\text{Signature} = \text{HMAC-SHA256}\Big(\text{Canonical}(\text{manifest\_without\_sig}), \mathcal{K}_{\text{backup}}\Big)$$
3. **Restore Gating:** During restore (`restore_backup`), the signature is validated. If the archive has been modified or signature is absent, restore aborts immediately before any database queries execute.

### 6.2 Optional AES-256-GCM Authenticated Encryption
To protect faculty PII (salary, PAN, medical certificates) when backups are transported off-site:
- Backup archives can be encrypted using `encrypt_backup_file()`.
- Uses **AES-256-GCM** (Galois/Counter Mode) providing both confidentiality and cryptographic authentication.
- Key derivation: Scrypt ($N=16384, r=8, p=1, \text{dklen}=32$).
- Wire format: `ENCB` (4-byte magic) + 16-byte Salt + 12-byte GCM Nonce + Ciphertext (with 16-byte Poly1305 authentication tag).

---

## 7. Dynamic Rotating Kiosk QR (TOTP-Style Replay Defense)

### 7.1 Vulnerability of Static QR Codes
In legacy biometric kiosk systems, displaying a static URL allows employees to photograph the QR code with their phone, forward it to peers, or bookmark the link, enabling proxy punches from remote locations.

### 7.2 Rotating Token Specification (`utils/kiosk_token.py`)
The terminal generates a fresh cryptographic token every 15–30 seconds:
$$\text{Window} = \left\lfloor \frac{\text{EpochSeconds}}{30} \right\rfloor$$
$$\text{Nonce} = \text{Hex}(\text{RandomBytes}(8))$$
$$\text{Signature} = \text{HMAC-SHA256}\Big(\text{Window} \parallel \text{":"} \parallel \text{Nonce}, \mathcal{K}_{\text{kiosk}}\Big)$$
$$\text{Token} = \text{Window} \parallel \text{":"} \parallel \text{Nonce} \parallel \text{":"} \parallel \text{Signature}$$

### 7.3 Validation & Single-Use Replay Protection
When the mobile client submits a punch request:
1. **Window Drift Check:** Verifies token window is within current or immediately preceding window (max 30s latency).
2. **Signature Verification:** Verifies HMAC-SHA256 signature against $\mathcal{K}_{\text{kiosk}}$.
3. **Replay Cache Check:** Checks in-memory cache `_USED_KIOSK_TOKENS`. If the token was previously consumed, the punch is rejected with `REPLAY_ATTACK_DETECTED`.
4. **Token Consumption:** Upon successful validation, the token is added to the cache, preventing reuse.

---

## 8. Biometric Data Protection & India DPDP Act 2023 Compliance

Faculty biometric check-in is engineered in strict compliance with the **Digital Personal Data Protection Act, 2023 (DPDP Act 2023)** enacted by the Parliament of India:

### 8.1 Zero Server-Side Biometric Storage (Section 4 & 6)
- **Principle of Purpose Limitation & Data Minimisation:** The institutional server **never collects, stores, or processes raw fingerprint images, minutiae data, or facial biometric templates**.
- **FIDO2 / WebAuthn Client Biometrics:** Biometric authentication is performed strictly on the employee's personal mobile device using native OS biometric hardware (Apple TouchID/FaceID Secure Enclave, Android BiometricPrompt Keymaster/TEE).
- The device verifies the fingerprint locally and releases only an asymmetrically signed cryptographic challenge (`biometric_proof`) to the server.

### 8.2 Lawful Consent & Notice (Section 5)
- Prior to enrollment, faculty are presented with clear institutional notice specifying that biometric validation is utilized solely for duty presence verification during official shift hours.
- In compliance with Section 6(1), alternate attendance verification options (e.g., RFID badge / HOD manual override) are available for staff who decline mobile biometric verification.

### 8.3 Data Retention Limitation (Section 8(7))
- Attendance records (check-in timestamp, late minutes, status) are retained strictly in accordance with academic accreditation audit cycles (AICTE/NAAC 5-year requirement).
- Cold archival (`services/backup_service.py`) automatically migrates aged attendance data into encrypted, read-only institutional archives.
