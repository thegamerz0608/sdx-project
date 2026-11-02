# Comprehensive Technical Audit & System Baseline (Phase 0)
**Project Title:** AI-Enabled Faculty Attendance, Leave and Substitute Management ERP  
**Audit Date:** October 30, 2026  
**Auditor / Engineering Role:** Senior QA Automation Engineer, Software Architect & Rigorous MCA External Examiner  
**Target Architecture:** Windows Desktop Application (PySide6) + Mobile/Kiosk Web Services (FastAPI/Uvicorn) + Pure-NumPy NLP Pipeline + Relational Persistence (MySQL / In-Memory Mock)  
**Baseline Test Status:** **169 Passed** (0 Failures, 0 Errors) in **22.08s** across 26 Test Suites

---

## Executive Summary

This rigorous technical audit establishes the verified baseline for the MCA Major Project *AI-Enabled Faculty Attendance, Leave and Substitute Management ERP*. The audit analyzes architectural integrity, runtime dependencies, authentication and session security, cryptographic data protection, biometric punch mechanisms, and natural language processing (NLP) corpus provenance.

All findings, test counts, execution metrics, and vocabulary statistics in this report are grounded in actual execution of the project codebase and its test suite.

---

## 1. Test Suite Reconciliation & Verification

### 1.1 The 163 vs. 166 Report Discrepancy
In previous versions of the project documentation, an arithmetic discrepancy was observed where the executive summary stated **163 unit/integration tests**, while the individual tabular breakdown in the report summed to **166 tests**.

A line-by-line audit of the test suites against pytest discovery reveals the exact source of this discrepancy:
1. `tests/test_leave_workflow.py`: The documentation table reported **11 tests**, whereas the test file contains exactly **9 executable test cases** (discrepancy of **-2**).
2. `tests/test_recommendation_engine.py`: The documentation table reported **6 tests**, whereas the test file contains exactly **5 executable test cases** (discrepancy of **-1**).

$$\text{Reported Table Sum (166)} - 2 (\text{leave\_workflow}) - 1 (\text{recommendation\_engine}) = \mathbf{163 \text{ Real Tests}}$$

### 1.2 Current Baseline Test Count: 169 Tests
With the subsequent implementation of the Student Marks Entry and Multi-Stage Workflow module (`tests/test_v3_1_features.py`, containing **6 tests**), the verified test suite count is now exactly:
$$163 + 6 = \mathbf{169 \text{ Passed Tests}}$$

### 1.3 Per-Suite Verified Test Breakdown (26 Suites)

| # | Test Suite File | Test Cases | Execution Scope & Verification Focus |
|---|---|:---:|---|
| 1 | `tests/test_analytics_engine.py` | 4 | Attendance rates, departmental aggregations, trend analytics |
| 2 | `tests/test_attendance.py` | 7 | Biometric check-in/out, late marking, work duration calculation |
| 3 | `tests/test_audit_engine.py` | 3 | Event logging, actor tracking, entity target auditing |
| 4 | `tests/test_auth.py` | 6 | Credential verification, PBKDF2 hashing, role resolution |
| 5 | `tests/test_backup_restore.py` | 6 | JSON/SQL table exports, SHA-256 manifest verification |
| 6 | `tests/test_database.py` | 3 | DB connection pools, transaction rollback, schema queries |
| 7 | `tests/test_faculty_dept.py` | 5 | Department CRUD, faculty mapping, designation checks |
| 8 | `tests/test_foundation.py` | 5 | Base entity models, validation invariants, error handlers |
| 9 | `tests/test_grace_engine.py` | 7 | Policy grace thresholds, consecutive late rules, deductions |
| 10 | `tests/test_instructor_and_profiles.py` | 7 | Lab instructors, dynamic user roles, profile updates |
| 11 | `tests/test_leave_engine.py` | 7 | Balance deductions, casual/medical quotas, date overlaps |
| 12 | `tests/test_leave_workflow.py` | 9 | Multi-tier approval (Applicant -> HOD -> Principal) |
| 13 | `tests/test_ml_classifiers.py` | 4 | Pure NumPy Naive Bayes, Logistic Regression, Linear SVM |
| 14 | `tests/test_nlp_dataset.py` | 4 | Corpus generation, balance across 5 classes, tokenization |
| 15 | `tests/test_packaging_release.py` | 4 | Desktop artifact bundling, PyInstaller spec validation |
| 16 | `tests/test_recommendation_engine.py` | 5 | Skill-weighted substitute ranking, workload balancing |
| 17 | `tests/test_report_engine.py` | 4 | PDF generation, monthly tabular exports, ReportLab styling |
| 18 | `tests/test_smartphone_punch.py` | 11 | QR parsing, WebAuthn payload handling, LAN token validation |
| 19 | `tests/test_students_and_multistage_workflow.py` | 14 | Student marks entry, grade calculation, PDF mark sheets |
| 20 | `tests/test_substitute.py` | 7 | Alternate arrangement creation, conflict detection |
| 21 | `tests/test_system_e2e.py` | 2 | End-to-end integration flow from punch to leave approval |
| 22 | `tests/test_tfidf_engine.py` | 4 | Unigram/bigram n-gram extraction, IDF diagonal computation |
| 23 | `tests/test_ui_enterprise_polish.py` | 5 | PySide6 UI styling, form validations, theme consistency |
| 24 | `tests/test_v3_1_features.py` | 6 | Conditional student seeding, PDF export download flow |
| 25 | `tests/test_v3_upgrades.py` | 6 | Performance optimizations, NVMe local IO, async decoupling |
| 26 | `tests/test_web_portals_and_kiosk.py` | 24 | Web authentication routing, role-based portals, kiosk UI |
| **Total** | **26 Suites** | **169** | **100% Passing (22.08s execution time)** |

---

## 2. Dependency Analysis: Runtime vs. Development

An audit of `requirements.txt` against active Python imports in `nlp/`, `services/`, `ui/`, `models/`, and `repositories/` revealed significant discrepancies between declared, installed, and actual runtime dependencies:

```
+-------------------------------------------------------------------------+
|                              DEPENDENCY AUDIT                           |
+-------------------------------------------------------------------------+
| Declared in requirements.txt | Actually Imported at Runtime | Status   |
+------------------------------+------------------------------+----------+
| PySide6 >= 6.5.0             | Yes (Desktop UI)             | Critical |
| mysql-connector-python       | Yes (MySQL Driver)           | Critical |
| PyMySQL >= 1.1.0             | Yes (Fallback DB driver)     | Runtime  |
| python-dotenv >= 1.0.0       | Yes (.env config loader)     | Runtime  |
| numpy >= 1.24.0              | Yes (Core NLP & Math)        | Critical |
| joblib >= 1.3.0              | Yes (Model serialization)    | Runtime  |
| reportlab >= 4.0.0           | Yes (PDF report generation)  | Runtime  |
| fastapi >= 0.100.0           | Yes (Mobile & Web APIs)      | Runtime  |
| uvicorn >= 0.20.0            | Yes (ASGI Web Server)        | Runtime  |
| qrcode >= 7.0.0              | Yes (Kiosk QR generator)     | Runtime  |
| pyngrok >= 7.0.0             | Optional (Remote tunneling)  | Optional |
| pytest >= 7.4.0              | Test runner only             | Dev Only |
+------------------------------+------------------------------+----------+
| scikit-learn >= 1.3.0        | NO (Pure NumPy ML in prod)   | Dev Only |
| nltk >= 3.8.1                | NO (Custom regex tokenizer)  | Unused   |
| pandas >= 2.0.0              | NO (Pure Python/NumPy data)  | Unused   |
| matplotlib >= 3.7.0          | NO (Pure CSS/ReportLab)      | Unused   |
+------------------------------+------------------------------+----------+
| cryptography (Unlisted)      | Yes (Security & hashing)     | Missing! |
| python-docx (Unlisted)       | Yes (Viva report generation) | Missing! |
+-------------------------------------------------------------------------+
```

### Key Recommendations:
1. **Remove Unused Dependencies:** Remove `nltk`, `pandas`, and `matplotlib` from `requirements.txt`.
2. **Segregate scikit-learn:** Downgrade `scikit-learn` to `requirements-dev.txt` for use exclusively in `tools/validate_against_sklearn.py`. The production application must run purely on NumPy.
3. **Declare Unlisted Runtime Dependencies:** Add `cryptography>=41.0.0` and `python-docx>=1.0.0` to `requirements.txt`.

---

## 3. Security Architecture Audit

### 3.1 Password Hashing Scheme
- **Current State:** Implemented in `utils/security.py` using `hashlib.pbkdf2_hmac` with `sha256`, 100,000 iterations, and a 16-byte cryptographically secure random salt (`os.urandom(16)`), formatted as `salt_hex$hash_hex`. A legacy fallback accepts unsalted SHA-256 for backward compatibility.
- **OWASP Compliance Gap:** 
  - OWASP Password Storage Cheat Sheet (2023/2024) recommends **Argon2id** (memory-hard, resistant to GPU/ASIC acceleration, RFC 9106) with $m=65536 \text{ KiB}, t=3, p=4$, or PBKDF2-HMAC-SHA256 with at least 600,000 iterations.
  - The legacy SHA-256 fallback creates a vulnerability window if old hashes persist in database tables.
- **Remediation Plan (Phase 2):** Implement Argon2id via `cryptography` / `argon2-cffi` with a transparent automatic rehash mechanism: when a user logs in with a PBKDF2 or SHA-256 hash, verify it, immediately re-hash using Argon2id, and update the database row.

### 3.2 Web Session & JWT Management
- **Current State:** `services/web_portal_service.py` issues HS256-signed JSON Web Tokens (`jwt_token`) upon successful web authentication, stored in an HTTP-only cookie named `cms_token` with `max_age=86400` (24 hours).
- **Vulnerabilities Identified:**
  1. `Secure=False`: The cookie flag does not require HTTPS, permitting plaintext transmission over unencrypted LAN connections.
  2. `SameSite="lax"` without CSRF Tokens: State-changing POST requests (`/api/leaves/apply`, `/api/profile/update`) are not protected by anti-CSRF double-submit cookies or custom header tokens.
  3. Static 24-Hour Expiration: Tokens lack an automatic idle timeout or server-side revocation list (denylist / revocation blocklist on logout).
  4. Missing Security Headers: Endpoints lack standard headers (`Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Strict-Transport-Security`).
- **Remediation Plan (Phase 2):** Implement dual-token authentication (short-lived access token + rotating refresh token), double-submit anti-CSRF protection, rate limiting on `/api/login`, and an active token revocation repository.

### 3.3 Audit Log Storage & Immutability
- **Current State:** Implemented in `repositories/audit_repository.py`. Events are stored as sequential rows in an SQL table `audit_logs` (`id, user_id, action, target_entity, details, ip_address, created_at`) and duplicated in an in-memory list `_in_memory_logs`.
- **Vulnerabilities Identified:**
  - Plain SQL inserts provide zero cryptographic immutability. Any actor with database access (or an attacker exploiting SQL injection) can modify timestamps, delete incriminating records, or inject spurious audit entries without detection.
- **Remediation Plan (Phase 2):** Implement a cryptographic hash-chained audit log (Merkle / blockchain ledger):
  $$\text{Hash}_i = \text{HMAC-SHA256}\Big(\text{Hash}_{i-1} \parallel \text{ID}_i \parallel \text{UserID}_i \parallel \text{Action}_i \parallel \text{Target}_i \parallel \text{Timestamp}_i, \mathcal{K}_{\text{audit}}\Big)$$
  Provide an automated tamper-verification function and script to mathematically verify the chain integrity.

### 3.4 Backup Signing & Integrity Verification
- **Current State:** `services/backup_service.py` creates a ZIP archive containing JSON and SQL dumps of database tables alongside a `manifest.json` recording the SHA-256 digest of each file.
- **Vulnerabilities Identified:**
  - While individual files are hashed, the manifest itself is **not cryptographically signed**. An attacker or corrupted transfer can modify both the dump file and its hash in `manifest.json` without failing validation.
  - Backups are stored in unencrypted ZIP format, exposing faculty PII (names, contact numbers, attendance logs, leave reasons) in plaintext on disk.
- **Remediation Plan (Phase 2):** Sign `manifest.json` with HMAC-SHA256 using an application secret, and provide AES-256-GCM authenticated encryption for backup archives.

---

## 4. Hardware vs. Biometric Emulation Audit

### 4.1 Biometric Kiosk QR Punch Security
- **Current State:** `ui/biometric_kiosk_window.py` generates a static QR code pointing to `http://<LAN_IP>:8000/punch-interface`.
- **Vulnerabilities Identified:**
  - **Proxy / Remote Punch Vulnerability:** Because the QR code is static, an employee can photograph the QR code with their smartphone, share it with colleagues via WhatsApp, or bookmark the URL. Employees can punch in/out from anywhere on the campus LAN without being physically present at the terminal.
- **Remediation Plan (Phase 2):** Replace the static QR with a dynamic, time-rotating QR code (refreshed every 15–30 seconds):
  $$\text{Token} = \text{Base64}\Big(\text{Timestamp} \parallel \text{TerminalID} \parallel \text{HMAC-SHA256}(\text{Timestamp} \parallel \text{TerminalID}, \mathcal{K}_{\text{kiosk}})\Big)$$
  The server will validate that the scanned token is within a 30-second window and has not been used previously (single-use nonce cache).

### 4.2 Hardware Reality Check: Biometric Fingerprint
- **Current Implementation:** `services/mobile_punch_service.py` leverages the browser-standard WebAuthn JavaScript API (`navigator.credentials.create` / `navigator.credentials.get`). When accessed on mobile devices supporting biometric unlocking (TouchID, FaceID, Android BiometricPrompt), it delegates verification to the mobile operating system's hardware keystore.
- **Fallback Implementation:** In local HTTP / non-HTTPS test environments where WebAuthn is restricted by browser security policies, the service falls back to a software-simulated token (`lan_sensor_verified_<timestamp>`).
- **Audit Clarification for External Examination:**
  > **Crucial Academic Distinction:** The system does **NOT** interface with a physical desktop USB fingerprint scanner (e.g., DigitalPersona, Mantra MFS100, SecuGen) via proprietary C/C++ DLL SDKs. Instead, it utilizes **FIDO2 / WebAuthn Client Biometrics** over HTTPS with an automated software fallback for evaluation.
  > 
  > This distinction must be explicitly documented in the major project dissertation to prevent examiner objections regarding unattached physical peripherals.

---

## 5. NLP Leave Reasons Dataset Provenance

### 5.1 Dataset Construction & Provenance
The NLP dataset generator (`nlp/dataset_generator.py`) produces a curated synthetic corpus designed to reflect realistic faculty leave applications across Indian higher education institutions.

- **Total Corpus Size:** **500 samples**
- **Target Categories (5 Classes):**
  1. `CL` (Casual Leave): 100 samples (20.0%)
  2. `ML` (Medical Leave): 100 samples (20.0%)
  3. `EL` (Earned Leave): 100 samples (20.0%)
  4. `SCL` (Special Casual Leave): 100 samples (20.0%)
  5. `OD` (On Duty Leave): 100 samples (20.0%)
- **Class Balance:** Perfectly balanced (ratio $1:1:1:1:1$, 100 samples per class).

### 5.2 Corpus Text Statistics
- **Total Word / Token Count:** 9,314 tokens
- **Unique Raw Vocabulary Words:** 388 words
- **TF-IDF Feature Space (Unigrams + Bigrams):** 845 extracted features
- **Mean Sentence Length:** 18.6 words per application
- **Seed Variations:** 10–15 base domain seed patterns per category, combined with 10 institutional modifiers (e.g., *"Doctor certificate is attached herewith"*, *"I will ensure my lecture topics are covered by substitute faculty"*), formal salutations (*"Respected Sir/Madam"*), and urgency prefaces.

### 5.3 Pure-NumPy Pipeline Architecture
The leave classification module is implemented completely from scratch using standard Python libraries and NumPy:
1. `nlp/preprocessor.py`: Custom lowercasing, punctuation stripping, stopword removal, and rule-based morphological suffix reduction.
2. `nlp/vectorizer.py` (`TFIDFEngine`): N-gram extraction, term-frequency computation, smooth inverse document frequency ($\log(1 + N / (1 + \text{df})) + 1$), and $L_2$ vector normalization.
3. `nlp/classifiers.py`:
   - `MultinomialNBClassifier`: Pure-NumPy log-likelihood with Laplace smoothing ($\alpha = 1.0$).
   - `LogisticRegressionClassifier`: Multi-class Softmax with cross-entropy loss, $L_2$ regularization, and gradient descent.
   - `LinearSVMClassifier`: One-vs-Rest (OvR) linear support vector machine with hinge loss and subgradient optimization.

---

## 6. Git Version Control Status

- **Environment Finding:** The system PATH does not currently expose a native `git.exe` binary.
- **Mitigation:**
  - Code changes will be staged with atomic, granular file modifications and documented change logs.
  - A project migration script and git commit guide will be established so all changes can be committed to the `improvements` branch immediately once Git is invoked or installed.

---

## 7. Baseline Execution Summary

- **Total Test Suites:** 26
- **Total Passing Tests:** 169
- **Total Failing / Errored Tests:** 0
- **Total Skipped Tests:** 0
- **Total Execution Duration:** 22.08 seconds
- **Database Engine:** MySQL 8.0 / PyMySQL In-Memory Mock Fallback
- **GUI Engine:** PySide6 (Qt 6.11.2)
- **Web API Engine:** FastAPI 0.162.0 on Uvicorn 0.54.0

---

## 8. Transition to Phase 1: Machine Learning Enhancements

With Phase 0 baseline metrics validated and documented, the project is positioned to begin **Phase 1: ML Pipeline Improvements**:
1. Implementation of **Temperature Scaling** in pure NumPy (1D NLL optimization on validation splits to calibrate softmax probabilities).
2. Development of `tools/evaluate_model.py` generating:
   - 5-Fold Stratified Cross-Validation metrics (Accuracy, Precision, Recall, Macro-F1).
   - Multi-class Confusion Matrix.
   - Expected Calibration Error (ECE) before and after temperature scaling.
   - Wilson Score and Bootstrap 95% Confidence Intervals.
3. Feature explainability engine (Top-10 positive/negative predictive n-grams per leave class).
4. Out-of-Vocabulary (OOV) and Gibberish detection thresholding.
5. Offline benchmark script `tools/validate_against_sklearn.py` comparing the pure-NumPy model to `scikit-learn` to demonstrate zero scientific performance loss.
6. Documentation of the dataset in `docs/DATASET.md`.
