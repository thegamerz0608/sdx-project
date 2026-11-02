# AI-Enabled Faculty Attendance, Leave and Substitute Management ERP

[![Platform](https://img.shields.io/badge/Platform-Windows_Desktop-0078D7.svg)](https://www.microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.14-3776AB.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PySide6_%28Qt6%29-41CD52.svg)](https://doc.qt.io/qtforpython-6/)
[![Database](https://img.shields.io/badge/Database-MySQL_8.0-4479A1.svg)](https://www.mysql.com/)
[![ML-Engine](https://img.shields.io/badge/ML--Engine-Pure_NumPy_%28Sublinear_TF--IDF%29-013243.svg)](https://numpy.org/)
[![Tests](https://img.shields.io/badge/Tests-93%2F93_Passing-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/Release-Production_v1.0.0-blue.svg)]()

> **Master of Computer Applications (MCA) Major Project**  
> **Institution:** A.J. Institute of Engineering & Technology, Mangaluru  
> **Student:** Shashank Poojary  

---

## 1. Executive Summary

The **AI-Enabled Faculty Attendance, Leave and Substitute Management ERP** is an enterprise-grade desktop application engineered for higher educational institutions. It eliminates administrative inefficiencies by unifying biometric attendance punch reconciliation, automated monthly grace tracking, institutional leave policy enforcement, natural-language leave reason classification via Machine Learning, and conflict-free substitute faculty allocation with fair workload distribution.

---

## 2. Key Architecture & Features (All 18 Phases Complete)

### 🖥️ Desktop User Interface (PySide6 / Qt6)
- **16-Tab Enterprise Workspace:**
  1. **System Dashboard:** Live database engine diagnostics, real-time connectivity monitor, execution log.
  2. **Faculty Roster:** Multi-column directory of faculty, designations, departments, and active statuses.
  3. **Department Management:** Academic departments, HOD assignments, and workload quotas.
  4. **Attendance Management:** Biometric CSV punch ingestion, anomaly flagging, and manual record adjustments.
  5. **Grace & Policy Engine:** Automated monthly 60-minute grace ledger and late arrival tracking.
  6. **Leave Policy & Entitlements:** Master leave rules (CL, ML, EL, OD, SCL, etc.) and entitlement rules.
  7. **Leave Applications & Approvals:** Faculty leave submission with real-time AI category inference.
  8. **Substitute Management:** Timetable conflict detection and fair-load substitute peer recommendations.
  9. **NLP Classifier & Corpus:** Curated 500-sample balanced ground-truth dataset across 10 classes.
  10. **TF-IDF Feature Matrix:** Unigram/bigram token vocabulary inspector and inverse document frequencies.
  11. **ML Classifiers & Benchmarks:** Multinomial Naive Bayes, Linear SVM, and Softmax Logistic Regression.
  12. **AI Recommendation Engine:** Multi-factor policy risk assessment score ($0–100$) and auto-feasibility flags.
  13. **Attendance Analytics Engine:** Monthly punctuality trends, late arrival clustering, and absence anomaly detection.
  14. **Institutional Report Generator:** 1-click official PDF generation (ReportLab) and CSV dataset exports.
  15. **Audit Trail Explorer:** Append-only security audit log recording user actions, IP addresses, and timestamps.
  16. **System Maintenance & Backup:** Full `.zip` snapshots with SHA-256 manifests, `.json.gz` cold data archival, and system health diagnostics.

### 🧠 Pure-NumPy Machine Learning & NLP Engine
- **Zero-Dependency Inference:** Developed using fundamental mathematical principles in pure NumPy, ensuring 100% operational reliability on Windows enterprise systems without requiring SciPy C-compiler DLLs.
- **Feature Extraction:** Sublinear Term Frequency ($1 + \ln(\text{count})$), Smoothed Inverse Document Frequency ($\ln((1+N)/(1+\text{DF})) + 1$), and $L_2$ vector normalization producing an 845-dimensional feature space.
- **High-Accuracy Production Classifier:** Softmax Logistic Regression delivering **95.00% Accuracy** and **0.951 Macro F1-Score** with calibrated posterior confidence probabilities.

### 🗄️ Relational Database & Offline Resilience
- **Third Normal Form (3NF) MySQL Schema:** 12 normalized tables (`users`, `departments`, `faculty_profiles`, `attendance`, `grace_minutes`, `leave_applications`, `substitute_assignments`, etc.).
- **In-Memory Circuit Breaker Fallback:** If MySQL server is temporarily offline, the ERP seamlessly switches to in-memory mock repositories without crashing.

---

## 3. Quick Start & Execution

### Option A: 1-Click Launch (Recommended)
Simply double-click:
```cmd
run_app.bat
```
*This script automatically checks the virtual environment, starts XAMPP MySQL (if present), and launches the desktop ERP interface.*

### Option B: Automated Setup & Installation
For first-time setup or dependency installation:
```cmd
setup_environment.bat
```

### Option C: Manual Terminal Execution
```cmd
# 1. Activate virtual environment
venv\Scripts\activate.bat

# 2. (Optional) Initialize MySQL database tables
python database\init_db.py

# 3. Launch application
python main.py
```

---

## 4. Default Login Credentials (RBAC)

The system enforces strict Role-Based Access Control (RBAC):

| Role | Username | Password | Permitted Capabilities |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` | Full access: User management, biometric CSV import, classifier re-training, system backups, audit trails. |
| **Head of Department (HOD)** | `hod_mca` | `hod123` | Department roster, punctuality analytics, AI leave screening review, substitute duty assignments. |
| **Faculty Member** | `faculty_f001` | `faculty123` | Personal attendance ledger, monthly grace balance, leave applications with real-time AI prediction, substitute duty invitations. |

---

## 5. Standalone Executable Packaging (PyInstaller)

To build a completely standalone Windows `.exe` distribution:
```cmd
build_exe.bat
```
The compiled release will be generated in `.\dist\FacultyERP\FacultyERP.exe`.

---

## 6. Automated Test Suite Verification

The project includes an exhaustive unit and end-to-end integration test suite covering all 18 phases:
```cmd
pytest
```
**Results:** **93 / 93 tests passing (100% pass rate) in ~14 seconds**.

---

## 7. Project Documentation Deliverables

* **Software Design Specification (SDS DOCX):** [SYSTEM_DESIGN_SPECIFICATION.docx](file:///d:/SNK(project)/SYSTEM_DESIGN_SPECIFICATION.docx)
* **Software Design Specification (SDS PDF):** [SYSTEM_DESIGN_SPECIFICATION.pdf](file:///d:/SNK(project)/SYSTEM_DESIGN_SPECIFICATION.pdf)
* **Software Requirements Specification (SRS DOCX):** [IEEE_SRS_Document.docx](file:///d:/SNK(project)/IEEE_SRS_Document.docx)
* **Software Requirements Specification (SRS PDF):** [IEEE_SRS_Document.pdf](file:///d:/SNK(project)/IEEE_SRS_Document.pdf)
* **Comprehensive Overall Report:** [PROJECT_OVERALL_REPORT.md](file:///C:/Users/shamith/.gemini/antigravity/brain/b107d1ae-5e5e-47c8-bf3f-37b49ee798bc/PROJECT_OVERALL_REPORT.md)
* **Project Presentation:** `Faculty_ERP_Presentation.pptx`
