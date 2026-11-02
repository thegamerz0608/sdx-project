# Software Requirements Specification
## for
# AI-Based Faculty Attendance, Leave & Substitute Management ERP
### Version 1.0
### Prepared by SHASHANK POOJARY
**Department of MCA**  
**Batch 2025–2027**  
**Date:** October 2026  

---

## Table of Contents
* **Table of Contents**
* **Revision History**
* **1. Introduction**
  * 1.1 Purpose
  * 1.2 Intended Audience
  * 1.3 Scope
  * 1.4 References
* **2. Overall Description**
  * 2.1 Product Perspective
  * 2.2 Product Functions
  * 2.3 User Classes and Characteristics
  * 2.4 Operating Environment
  * 2.5 Design and Implementation Constraints
  * 2.6 Assumptions and Dependencies
* **3. Specific Requirements**
  * 3.1 Data Requirements
  * 3.2 Functional Requirements (System Features)
  * 3.3 Performance and ML Quality Requirements
  * 3.4 External Interface Requirements
  * 3.5 Security and Safety Requirements
* **4. Appendices**
  * Appendix A: Glossary
  * Appendix B: Dataset Distribution & Database Schemas

---

## Revision History

| Name | Date | Reason For Change | Version |
| :--- | :--- | :--- | :--- |
| Shashank Poojary | 15/09/2026 | Initial Draft Creation | 1.0 |
| Shashank Poojary | 05/10/2026 | Finalized IEEE SRS Specifications | 1.0 |

---

## 1. Introduction

### 1.1 Purpose
This Software Requirements Specification (SRS) describes the requirements of the **AI-Based Faculty Attendance, Leave & Substitute Management ERP**. The main purpose of the system is to assist academic departments in automating faculty attendance processing, classifying natural language leave applications, tracking grace limits, and managing substitute faculty allocations using artificial intelligence.

The system takes raw biometric attendance log files (CSV/Excel) and natural-language faculty leave descriptions as input. It uses automated calculation logic to compute daily working hours, late minutes, and grace usage. Additionally, a machine learning text classification model categorizes free-text leave reasons into standardized institutional leave types (such as Casual Leave, Medical Leave, On Duty Leave, etc.) and provides a prediction confidence score to assist the Head of Department (HOD) during approval. When an approved leave requires teaching coverage, the system recommends available departmental faculty without schedule overlaps.

The system is intended to act as an intelligent decision-support tool for institutional administrators and HODs rather than fully replacing human authorization. It provides automated calculations, prediction confidence ratings, conflict detection, and attendance anomaly tracking. This SRS covers software features such as biometric data ingestion, attendance preprocessing, NLP leave classification, confidence scoring, substitute allocation, grace tracking, anomaly detection, and PDF/Excel report generation. Physical biometric hardware readers, door locks, and external institutional payroll software are outside the primary scope of this application.

### 1.2 Intended Audience
This SRS is mainly intended for project developers, guides, testers, and evaluators involved in developing and evaluating the system. It can also be used by institutional administrators, HODs, and faculty members who want to understand the features and operational capabilities of the proposed ERP.

The document first gives an overview of the system, its purpose, scope, and general description. The following sections explain the functional and non-functional requirements, system features, user interactions, and technical specifications.

It focuses on system features and detailed requirements to understand what needs to be implemented. Testers can refer to the functional and non-functional requirements to prepare comprehensive test cases. The project guide and evaluators can begin with the Introduction and Overall Description sections to understand the purpose, scope, and overall functionality of the project.

A recommended reading sequence is to start with the Introduction, followed by the Overall Description, and then the Specific Requirements and Appendices.

### 1.3 Scope
The proposed system is an AI-based faculty attendance, leave, and substitute management ERP designed for academic institutions. The system analyzes biometric check-in/check-out logs, calculates working hours and late minutes, processes free-text leave descriptions using machine learning, tracks monthly grace usage, and recommends substitute teachers for approved leave periods.

The main goal of the system is to support efficient administrative operations, reduce manual checking of attendance sheets, eliminate leave classification ambiguities, and prevent teaching schedule conflicts during faculty absences.

The system is intended to support HODs, administrators, and faculty members as an integrated decision-support desktop application. By combining automated biometric processing, NLP-based leave classification, grace tracking, substitute matching, and anomaly detection, the system aims to make faculty management transparent, consistent, and efficient.

### 1.4 References
1. IEEE Standard 830-1998: *IEEE Recommended Practice for Software Requirements Specifications*.
2. Pedregosa et al. (2011), *Scikit-learn: Machine Learning in Python*, Journal of Machine Learning Research, vol. 12, pp. 2825–2830.
3. McCallum & Nigam (1998), *A Comparison of Event Models for Naive Bayes Text Classification*, AAAI-98 Workshop on Learning for Text Categorization.
4. PySide6 / Qt6 Official Developer Documentation and API Reference.
5. MySQL 8.0 Reference Manual and Relational Database Standards.

---

## 2. Overall Description

### 2.1 Product Perspective
The proposed system is a desktop-based enterprise application developed to modernize faculty attendance, leave approval, and substitute scheduling using artificial intelligence. It is a standalone system built with Python, PySide6 (Qt framework), and a MySQL database.

The user can import biometric punch files (CSV/Excel) or enter natural-language leave applications. The attendance engine computes check-in times, working hours, and grace consumption. For leave applications, the trained text classification pipeline predicts the appropriate leave category along with a confidence score and highlights key terms influencing the result.

If approved leave creates a class timetable vacancy, the substitute module scans departmental faculty timetables to suggest available, conflict-free substitute teachers. The system can also highlight unusual attendance patterns (such as frequent late arrivals or grace limit exhaustion) over specified time periods.

The main parts of the system include the desktop user interface (PySide6 GUI), attendance processing engine, NLP classifier model, grace manager, substitute allocation engine, anomaly detector, and PDF/Excel reporting module.

### 2.2 Product Functions
The main functions of the proposed system are:
* Allow the administrator to import biometric attendance data from CSV or Excel files.
* Preprocess and validate biometric logs to calculate check-in time, check-out time, total working hours, and late minutes.
* Implement configurable grace logic to deduct late minutes from a monthly allowance.
* Allow faculty members to submit leave applications with natural-language reasons.
* Use the trained machine learning model to classify leave reasons into one of 10 institutional leave categories.
* Display prediction results and confidence scores to assist the HOD during leave approval.
* Recommend available, conflict-free substitute faculty members during approved leave periods.
* Track faculty substitute workload to ensure fair duty distribution.
* Detect statistical attendance anomalies, such as repeated late arrivals or irregular grace exhaustion.
* Enforce role-based access control (RBAC) for Admin, HOD, and Faculty users.
* Generate and export comprehensive attendance, leave, substitute, and analytics reports in PDF and Excel formats.

### 2.3 User Classes and Characteristics
The proposed system is designed for users who manage, approve, or submit faculty attendance and leave requests within an academic institution. The main user classes are:
* **System Administrator (Admin):** Responsible for managing user accounts, configuring shift timings, setting monthly grace thresholds, retraining ML models, backing up databases, and generating institution-wide audit reports. High technical proficiency is expected.
* **Head of Department (HOD):** Primary decision-makers for departmental leave approvals. They view pending applications, review AI leave predictions and confidence scores, assign substitute teachers, monitor grace consumption, and analyze department attendance trends. Moderate computer knowledge is required.
* **Faculty Members:** Standard users of the system. They submit leave requests with free-text reasons, view personal attendance histories, check remaining leave balances and grace minutes, and view assigned substitute duties. Basic computer skills are sufficient.

Among these groups, HODs and Administrators are the most active decision-making users, while Faculty members use self-service portal features.

### 2.4 Operating Environment
The proposed system will operate on a standard computer or laptop capable of executing Python 3 and desktop GUI applications.
* **Operating System:** Microsoft Windows 10 or Windows 11 (64-bit), Linux (Ubuntu 20.04+), or macOS (12.0+).
* **Programming Language:** Python 3.10 / 3.11 / 3.14.
* **UI Framework:** PySide6 (Qt for Python).
* **Machine Learning Framework:** Scikit-learn, NumPy, Pandas, Joblib.
* **Database System:** MySQL Server 8.0 or MariaDB.
* **RAM:** Minimum 4 GB recommended (8 GB preferred for optimal ML training performance).
* **Storage:** At least 1 GB free space for application files, trained model binaries (`.joblib`), and database storage.
* **Network:** Localhost or LAN network connection to the MySQL database server.

### 2.5 Design and Implementation Constraints
The proposed system will be developed using Python and PySide6 for the desktop interface, with Scikit-learn for text classification models (Multinomial Naive Bayes, Logistic Regression, SVM). MySQL will serve as the relational database backend.

The system must run smoothly on standard institutional computers with at least 4 GB RAM. The accuracy of leave classification depends on the quality of training text data and model performance. Machine learning predictions are intended to assist HOD decision-making and should not replace human administrative review.

Uploaded data and user credentials must be handled securely. User passwords must be encrypted using salted `bcrypt` hashing, and database calls must use parameterized queries to block SQL injection. Long-running processing tasks (such as CSV bulk import or model training) must be executed on background worker threads (`QThread`) so the UI remains interactive.

### 2.6 Assumptions and Dependencies
The system assumes that biometric CSV/Excel files contain valid column headers (`Faculty_ID`, `Date`, `Punch_In`, `Punch_Out`) and readable timestamp values. It is assumed that faculty members enter clear, descriptive English text when requesting leave.

The system depends on the trained Scikit-learn model artifacts (`.joblib`) for leave reason classification. System execution relies on Python, PySide6, Scikit-learn, and MySQL connector libraries being properly installed in the runtime environment. Any alterations to database connection parameters or missing library dependencies will prevent the software from starting.

---

## 3. Specific Requirements

### 3.1 Data Requirements
The system uses natural-language leave application reasons and biometric punch logs for training, validation, testing, and operational execution. The leave classification dataset contains free-text descriptions categorized into 10 target institutional leave classes:
1. Casual Leave (CL)
2. Earned Leave (EL)
3. Academic Vacation Leave (AVL)
4. Special Casual Leave (SCL)
5. Medical Leave (ML)
6. Maternity Leave (MAT)
7. Paternity Leave (PAT)
8. On Duty Leave (OD)
9. Compensatory Leave (CPL)
10. Restricted Leave (RL)

Before training, text data is preprocessed by lowercasing, stripping special characters, removing stop words, and converting text into numerical TF-IDF (Term Frequency-Inverse Document Frequency) feature vectors using unigram and bigram ranges.

Biometric data tables store check-in, check-out, working hours, late minutes, and monthly grace consumption. User credentials and audit logs are stored securely in MySQL tables.

### 3.2 Functional Requirements (System Features)
* **Data Ingestion:** The system shall allow authorized users to select and import biometric CSV or Excel export files. Uploaded files shall be validated before computing daily attendance.
* **Attendance Processing:** The system shall calculate total working hours (`Punch_Out - Punch_In`) and determine late arrival minutes based on official shift start times.
* **Grace Minute Calculation:** The system shall deduct late minutes from a monthly configurable grace allowance (e.g., 60 minutes/month) and flag grace exhaustion.
* **NLP Leave Reason Classification:** The system shall take natural-language text entered during leave submission, vectorize it using TF-IDF, and pass it to the trained classifier.
* **Prediction Confidence:** The system shall calculate and display the probability confidence score alongside predicted leave categories to assist the HOD.
* **Substitute Faculty Allocation:** The system shall scan departmental faculty timetables to identify available, conflict-free substitute teachers for approved leave dates.
* **Workload Monitoring:** The system shall track assigned substitute duties for each faculty member to promote balanced distribution.
* **Attendance Anomaly Detection:** The system shall analyze attendance logs to flag irregular patterns, such as frequent late check-ins on specific weekdays or sudden absenteeism spikes.
* **Model Retraining:** The system shall allow administrators to retrain classifier models when updated dataset records become available, displaying comparative performance metrics (accuracy, F1-score) before updating binary model artifacts.
* **Reporting & Export:** The system shall generate monthly attendance summaries, leave registers, substitute reports, and anomaly logs, exportable as PDF and Excel files.

### 3.3 Performance and ML Quality Requirements
The system evaluates text classification model performance using accuracy, precision, recall, weighted F1-score, and confusion matrix analysis across test samples.

The trained ML model pipeline must satisfy the following minimum benchmarks:
* **Minimum Model Accuracy:** $\ge 85\%$ across 10-class leave evaluation.
* **Minimum Weighted F1-Score:** $\ge 0.85$.
* **Inference Response Latency:** Leave reason prediction must return results in $\le 200\text{ ms}$.
* **Biometric Ingestion Throughput:** Processing 1,000 punch records must complete in $\le 3\text{ seconds}$.
* **UI Responsiveness:** GUI screen navigation and modal transitions must open within $\le 100\text{ ms}$.

### 3.4 External Interface Requirements
The system shall provide a clean, modern desktop GUI built with PySide6. The interface includes a Login Dialog, Attendance View, Leave Submission Form, HOD Recommendation Panel, Substitute Management Window, Grace Configurator, Model Evaluation View, and Reporting Dashboard.

The backend service layer connects the PySide6 UI with Python processing services, Scikit-learn pipelines, and the MySQL database engine. Database interactions use parameterized SQL execution to ensure data safety.

Export services interact with `ReportLab` for PDF document generation and `openpyxl` / `XlsxWriter` for spreadsheet outputs.

### 3.5 Security and Safety Requirements
The system shall enforce Role-Based Access Control (RBAC) to ensure users access only features permitted for their role (`ADMIN`, `HOD`, `FACULTY`).

User passwords shall be hashed using salted `bcrypt` algorithms. All database queries shall use prepared statements to prevent SQL injection vulnerabilities. System actions (such as leave approvals, grace adjustments, and model retraining) shall be logged in an audit table with user IDs and timestamps.

AI predictions shall be presented as decision-support recommendations and not as final binding decisions. The system shall handle invalid input files gracefully without crashing.

---

## 4. Appendices

### Appendix A: Glossary
* **ERP (Enterprise Resource Planning):** Integrated management software used to automate institutional administrative tasks.
* **Biometric Attendance:** Automated logging of employee check-in and check-out times using hardware scanners.
* **NLP (Natural Language Processing):** Artificial intelligence techniques used to analyze and classify human text.
* **TF-IDF (Term Frequency-Inverse Document Frequency):** Numerical vectorization method reflecting word importance in a document corpus.
* **MNB (Multinomial Naive Bayes):** Probabilistic machine learning classifier suited for text classification.
* **SVM (Support Vector Machine):** Supervised learning model used for classification tasks.
* **Grace Minutes:** A monthly time buffer allowed for late arrivals before attendance penalties apply.
* **HOD (Head of Department):** Academic administrator responsible for departmental management and leave approvals.
* **RBAC (Role-Based Access Control):** Restricting system features based on user roles.

---

### Appendix B: Dataset Distribution & Database Schemas

#### 1. Dataset Class Distribution (10 Leave Categories)

| Category Name | Code | Typical Keywords | Target Share |
| :--- | :--- | :--- | :--- |
| Casual Leave | CL | personal work, urgent matter, family event | 10% |
| Earned Leave | EL | annual leave, vacation, personal travel | 10% |
| Academic Vacation Leave | AVL | semester break, academic vacation | 10% |
| Special Casual Leave | SCL | special event, institutional duty | 10% |
| Medical Leave | ML | fever, doctor appointment, hospital, unwell | 10% |
| Maternity Leave | MAT | delivery, maternity, prenatal, newborn | 10% |
| Paternity Leave | PAT | paternity, child care, newborn support | 10% |
| On Duty Leave | OD | conference, paper presentation, external examiner | 10% |
| Compensatory Leave | CPL | extra duty compensation, weekend work | 10% |
| Restricted Leave | RL | festival, restricted holiday, cultural event | 10% |

#### 2. Primary Database Schema DDL

```sql
-- 1. Users Table
CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('ADMIN', 'HOD', 'FACULTY') NOT NULL,
    faculty_name VARCHAR(100) NOT NULL,
    department_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Biometric Attendance Table
CREATE TABLE attendance (
    attendance_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    attendance_date DATE NOT NULL,
    punch_in TIME,
    punch_out TIME,
    working_hours DECIMAL(4,2),
    late_minutes INT DEFAULT 0,
    grace_used INT DEFAULT 0,
    status ENUM('PRESENT', 'LATE', 'HALF_DAY', 'ABSENT') NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 3. Leave Applications Table
CREATE TABLE leave_applications (
    application_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    leave_reason TEXT NOT NULL,
    applied_category VARCHAR(50),
    predicted_category VARCHAR(50),
    confidence_score DECIMAL(5,2),
    substitute_user_id INT,
    hod_status ENUM('PENDING', 'APPROVED', 'REJECTED') DEFAULT 'PENDING',
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

---
*End of Software Requirements Specification.*
