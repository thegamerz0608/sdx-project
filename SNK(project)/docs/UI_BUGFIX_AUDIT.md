# UI Architecture & Layout Bugfix Audit (Phase 0)

**Project:** AI-Enabled Faculty Attendance, Leave and Substitute Management ERP  
**Target Environment:** Windows 10/11 Desktop, PySide6 (Qt 6.7+), MySQL/MariaDB, 1366×768 resolution  
**Audit Date:** 2026-10-30  
**Baseline Test Execution:** `pytest -q` with `QT_QPA_PLATFORM=offscreen` → **197 passed in 82.54s (100% pass rate)**  
**Version Control Note:** The `git` CLI executable is not installed in the host system (`where.exe git` returned exit code 1; no `.git` repository folder present). All fixes are tracked deterministically through explicit audit records, diffs, and change manifests.

---

## 1. Catalog of All UI Classes (Views, Tabs, Dialogs & Windows)

The application user interface comprises 23 primary view components, 10 modal dialogs, 2 main windows, and 2 support widgets across the `ui/` package:

| Class Name | File | Base Class | Role / Purpose |
| :--- | :--- | :--- | :--- |
| `MainWindow` | `ui/main_window.py` | `QMainWindow` | Root application shell with collapsible sidebar and `QStackedWidget` page container |
| `LoginWindow` | `ui/login_window.py` | `QMainWindow` | Standalone enterprise authentication window with CAPTCHA and role presets |
| `LoginDialog` | `ui/login_dialog.py` | `QDialog` | Modal authentication switcher for in-session logout/re-login |
| `BiometricKioskWindow` | `ui/biometric_kiosk_window.py` | `QMainWindow` | Standalone biometric and QR clock-in/out terminal |
| `DashboardWidget` | `ui/dashboard_widget.py` | `QWidget` | Landing dashboard: circular avatar, KPI grid, quick actions, diagnostics & time simulation |
| `KPICard` | `ui/dashboard_widget.py` | `QFrame` | Reusable metric presentation card with animated status indicator |
| `FacultyView` | `ui/faculty_view.py` | `QWidget` | Faculty profile management, department filter, and search grid |
| `FacultyDialog` | `ui/faculty_view.py` | `QDialog` | Modal dialog for creating and editing faculty records with avatar upload |
| `DepartmentView` | `ui/department_view.py` | `QWidget` | Academic department catalog and HOD assignment |
| `DepartmentDialog` | `ui/department_view.py` | `QDialog` | Modal dialog for adding or editing academic departments |
| `AttendanceView` | `ui/attendance_view.py` | `QWidget` | Biometric attendance CSV import, roster view, and validation grids |
| `GraceView` | `ui/grace_view.py` | `QWidget` | Monthly late-arrival grace balance ledger and manual allowance adjustment |
| `AdjustAllowanceDialog` | `ui/grace_view.py` | `QDialog` | Modal dialog for adjusting individual faculty grace allowance |
| `LeaveRulesView` | `ui/leave_rules_view.py` | `QWidget` | Leave entitlement rules, sandwich policy inspector, and simulation sandbox |
| `AdjustEntitlementDialog` | `ui/leave_rules_view.py` | `QDialog` | Modal dialog for editing annual leave quota |
| `LeaveApplicationView` | `ui/leave_application_view.py` | `QWidget` | Leave request submission, alternate arrangement duty, and HOD approval inbox |
| `ReviewRemarksDialog` | `ui/leave_application_view.py` | `QDialog` | Modal dialog for approving or rejecting leave requests with remarks |
| `SubstituteView` | `ui/substitute_view.py` | `QWidget` | Automated substitute recommendation engine, roster, and conflict resolver |
| `SubstituteResponseDialog` | `ui/substitute_view.py` | `QDialog` | Modal dialog for substitute faculty acceptance or decline |
| `NLPView` | `ui/nlp_view.py` | `QWidget` | Pure-NumPy NLP preprocessing explorer, tokenizer inspection, and live testing |
| `FeatureView` | `ui/feature_view.py` | `QWidget` | TF-IDF vocabulary matrix, feature weight visualizer, and sparse inspector |
| `ModelView` | `ui/model_view.py` | `QWidget` | Model training leaderboard, real-time metrics, and live inference console |
| `RecommendationView` | `ui/recommendation_view.py` | `QWidget` | Rule-based decision heuristics, priority scoring, and leave evaluation |
| `AnalyticsView` | `ui/analytics_view.py` | `QWidget` | Department performance analytics, anomaly radar, and monthly trends |
| `ReportView` | `ui/report_view.py` | `QWidget` | Enterprise PDF report generator and CSV export workbench |
| `AuditView` | `ui/audit_view.py` | `QWidget` | Immutable security audit trail explorer and RBAC permission matrix |
| `BackupView` | `ui/backup_view.py` | `QWidget` | SHA-256 signed database backup creation, restoration, and archival |
| `InstructorManagementWidget` | `ui/instructor_view.py` | `QWidget` | Laboratory instructor administration, avatar support, and roster |
| `InstructorDialog` | `ui/instructor_view.py` | `QDialog` | Modal dialog for enrolling and editing lab instructors |
| `StudentSearchWidget` | `ui/student_view.py` | `QWidget` | Academic student directory, multi-field search, and profile inspection |
| `StudentProfileDialog` | `ui/student_view.py` | `QDialog` | Modal card dialog displaying detailed student profile and status |
| `StudentFormDialog` | `ui/student_view.py` | `QDialog` | Modal dialog for enrolling new students with photograph upload |
| `LeaveManagementWidget` | `ui/leave_management_widget.py` | `QWidget` | Administrative leave cancellation and emergency date modification |
| `ModifyDatesDialog` | `ui/leave_management_widget.py` | `QDialog` | Modal dialog for altering active leave start/end dates |
| `StationeryView` | `ui/stationery_view.py` | `QWidget` | Consumables requisition form and HOD approval ledger |
| `StudentMarksView` | `ui/student_marks_view.py` | `QWidget` | Multi-subject internal and semester marks entry grid with PDF generator |
| `Sidebar` | `ui/sidebar.py` | `QFrame` | Collapsible animated navigation bar with role-gated items |
| `SmartphonePunchWidget` | `ui/smartphone_punch_widget.py` | `QWidget` | QR-based mobile punch-in terminal and endpoint configurator |
| `EmptyStateWidget` | `ui/empty_state.py` | `QFrame` | Standard empty placeholder card for data tables |
| `LoadingOverlay` | `ui/worker.py` | `QWidget` | Semi-transparent modal busy spinner overlay |

---

## 2. Root Cause Analysis of the Four Known UI Bugs

### Bug 1: Leave Applications "Alternate Arrangement" Group Box Overlap
- **File & Lines:** [`ui/leave_application_view.py:158-256`](file:///d:/SNK(project)/ui/leave_application_view.py#L158-L256)
- **Symptom:** In the "Apply for Leave" tab, the nested "Alternate Arrangement (Substitute Faculty Duty)" group box fields (Substitute Faculty, Duty Date, Time Slot, Location, Work Description) overlap vertically with each other and with the parent leave application controls.
- **Root Cause:**
  1. The entire left application panel (`form_group`) contains over 15 vertical rows (faculty selector, type, 2 date inputs, half-day checkbox, reason text edit, AI category badge, nested substitute group box with 5 form rows, attachment row, and 2 action buttons). This entire hierarchy is packed directly into `tab_layout.addWidget(form_group, stretch=1)` with **NO `QScrollArea`**.
  2. On a standard 1366×768 desktop viewport (available client height ~540px after subtracting Windows taskbar, window titlebar, top navigation bar, and tab bar), the vertical layout is heavily constrained. Qt's layout solver compresses all child widgets below their preferred heights, causing nested form rows in `alt_group` to visually clip and overlap.
  3. `txt_alt_work` is instantiated as a single-line `QLineEdit` instead of a multi-line `QPlainTextEdit`, leaving insufficient room for descriptive instructions.
- **Planned Fix:**
  1. Wrap the entire left application form column in a `QScrollArea` configured with `setWidgetResizable(True)`, `setFrameShape(QFrame.NoFrame)`, and vertical scrollbar as needed.
  2. Implement `alt_group` with a clean `QFormLayout` with appropriate field spacing (8px) and margins (12px).
  3. Replace `txt_alt_work` with a `QPlainTextEdit` having `setMinimumHeight(60)` and placeholder text.
  4. Ensure all labels align cleanly to the left and input fields stretch to the right.

---

### Bug 2: Lab Instructors & Student Directory Visual Bleed-Through
- **File & Lines:** [`ui/main_window.py:414-416, 432-434`](file:///d:/SNK(project)/ui/main_window.py#L414-L434)
- **Symptom:** Switching to Tab 16 ("Lab Instructors") or Tab 17 ("Student Directory") causes the contents of the Security Audit View to render underneath or visibly mixed with the active view.
- **Root Cause:**
  1. In `MainWindow.update_user_ui()`, the following lines execute upon login:
     ```python
     is_admin = bool(role == "ADMIN")
     if hasattr(self, "audit_view"):
         self.audit_view.setEnabled(is_admin)
         self.audit_view.setVisible(is_admin)  # <-- BUG
     ```
     And for non-admin/guest:
     ```python
     if hasattr(self, "audit_view"):
         self.audit_view.setEnabled(False)
         self.audit_view.setVisible(False)
     ```
  2. In Qt, pages added to `QStackedWidget` have their visibility managed internally by `QStackedWidget.setCurrentIndex()`. Calling `.setVisible(True)` directly on a child page of `QStackedWidget` bypasses Qt's internal stack management! As a consequence, `self.audit_view` is forced to remain visible regardless of which stacked page is active. When the user switches to `InstructorManagementWidget` (index 16) or `StudentSearchWidget` (index 17), `AuditView` remains painted on screen, causing visual ghosting and bleed-through.
- **Planned Fix:**
  1. Remove `self.audit_view.setVisible(...)` entirely from `MainWindow.update_user_ui()`. Rely strictly on `QStackedWidget.setCurrentIndex(index)` and sidebar navigation permissions to control view visibility.
  2. Ensure `InstructorManagementWidget` and `StudentSearchWidget` set a solid background and have explicit `QVBoxLayout` roots that clear and repaint their entire geometry cleanly on show events.

---

### Bug 3: System Dashboard Quick Actions & Table Row Clipping
- **File & Lines:** [`ui/dashboard_widget.py:81-231`](file:///d:/SNK(project)/ui/dashboard_widget.py#L81-L231), [`ui/styles.py:211-215`](file:///d:/SNK(project)/ui/styles.py#L211-L215)
- **Symptom:** Action buttons inside table rows and the bottom elements of the System Dashboard (quick action workbench, diagnostics buttons, system time controller, activity console) are clipped vertically at 1366×768 resolution.
- **Root Cause:**
  1. In `ui/styles.py` (lines 211-215), the global enterprise stylesheet defines:
     ```css
     QTableWidget::item {
         padding: 9px 12px;
         border-bottom: 1px solid #F1F5F9;
         color: #1E293B;
     }
     ```
     With 9px top and 9px bottom padding (18px total) plus font ascent/descent (~16px), a cell requires at least 34px. When cell widgets such as buttons (26px-34px) are inserted, default table row heights (~22px-28px) result in severe vertical clipping unless `verticalHeader().setDefaultSectionSize(40)` or `ResizeToContents` is set.
  2. In `DashboardWidget`, the vertical layout stacks the welcome banner, 4 KPI cards, Quick Action workbench, Diagnostics group, Time Controller group, and Activity Log console directly in a `QVBoxLayout` without a `QScrollArea`. At 1366×768, the cumulative vertical height exceeds 850px, forcing the bottom cards off-screen or squishing action buttons.
- **Planned Fix:**
  1. Wrap `DashboardWidget`'s central content container in a `QScrollArea` with `setWidgetResizable(True)` so that at 1366×768 all cards, diagnostics buttons, and consoles remain fully scrollable and never clipped.
  2. Audit and standardize table row heights: set `verticalHeader().setDefaultSectionSize(40)` across all data tables hosting cell action buttons (`tbl_students`, `tbl_instructors`, `tbl_faculty`, `tbl_requests`, `tbl_apps`).
  3. In `ui/styles.py`, fine-tune `QTableWidget::item` padding to `6px 10px` to maintain comfortable readability without clipping text when default row sizing is used.

---

### Bug 4: Student Profile Modal Stuck on Grey Skeleton
- **File & Lines:** [`ui/student_view.py:48-120`](file:///d:/SNK(project)/ui/student_view.py#L48-L120)
- **Symptom:** Opening the Student Profile modal from the Student Directory hangs on an unresolving grey skeleton if a background data fetch throws or fails to emit completion.
- **Root Cause:**
  1. In `StudentProfileDialog`, the component was originally implemented as a basic synchronous dialog without asynchronous loading infrastructure, animated skeleton state, or error recovery.
  2. When background loading was attempted, missing worker reference retention, unhandled database connection timeouts, and missing `error` signal connections left the skeleton widget visible indefinitely with no error feedback or retry option.
- **Planned Fix:**
  1. Refactor `StudentProfileDialog` to implement an asynchronous background loading pattern using `WorkerThread` or `QRunnable`.
  2. Implement explicit `skeleton_container` and `content_container` within a `QStackedLayout` or visibility toggle.
  3. Wire both `finished` and `error` signals:
     - On `finished`: populate student details, circular avatar, and academic metrics; hide skeleton; show content.
     - On `error`: hide skeleton; display an inline error banner with descriptive failure message and an interactive "🔄 Retry" button.
  4. Ensure proper thread cleanup with `worker.deleteLater()` on completion or rejection.
  5. Add unit regression tests in `tests/test_student_profile_dialog.py` verifying both success and error/retry pathways under offscreen Qt execution.

---

## 3. Comprehensive Layout & Geometry Audit Table

The following table catalogs every sizing constraint, positioning call, missing layout/scroll area, parenting anomaly, and stylesheet issue identified across the codebase:

| File | Line | Component / Symbol | Issue | Planned Fix |
| :--- | :--- | :--- | :--- | :--- |
| `ui/leave_application_view.py` | 158–256 | `_build_apply_tab` | Over 15 vertical form rows packed in `tab_layout` with NO `QScrollArea`; squashes `alt_group` at 1366×768 | Wrap left panel in `QScrollArea(widgetResizable=True)`; convert `alt_group` to structured `QFormLayout` |
| `ui/leave_application_view.py` | 227–229 | `txt_alt_work` | Instantiated as single-line `QLineEdit`; insufficient for duty instructions | Replace with `QPlainTextEdit(setMinimumHeight=60)` |
| `ui/main_window.py` | 416, 434 | `self.audit_view.setVisible(is_admin)` | Directly calls `setVisible` on `QStackedWidget` child page; overrides stack visibility and causes bleed onto other tabs | Remove `.setVisible()` calls; manage page visibility strictly via `QStackedWidget.setCurrentIndex` |
| `ui/dashboard_widget.py` | 81–231 | `_init_ui` | High-density dashboard (>850px) placed directly in `QVBoxLayout` without `QScrollArea`; clips at 1366×768 | Embed dashboard contents in a `QScrollArea(widgetResizable=True)` |
| `ui/student_view.py` | 48–120 | `StudentProfileDialog` | Missing robust async worker lifecycle, skeleton state, error signal handling, and retry UI | Implement `QStackedLayout` with skeleton/content/error views, wire `finished`/`error` signals, add retry button |
| `ui/styles.py` | 211–215 | `QTableWidget::item` | Excessive vertical padding (`9px 12px` = 18px total) causes row clipping when default table section sizes are used | Adjust padding to `6px 10px`; enforce `verticalHeader().setDefaultSectionSize(40)` on tables with action buttons |
| `ui/department_view.py` | 52 | `DepartmentDialog.setFixedSize(420, 320)` | Fixed dialog dimensions cannot expand if system DPI scaling (125%/150%) or localized fonts enlarge text | Replace with `setMinimumSize(420, 320)` and let `QLayout` manage natural resizing |
| `ui/faculty_view.py` | 60 | `FacultyDialog.setFixedSize(500, 540)` | Fixed dialog size may clip bottom save buttons on high DPI displays | Replace with `setMinimumSize(500, 540)` |
| `ui/grace_view.py` | 51 | `AdjustAllowanceDialog.setFixedSize(420, 260)` | Fixed size prevents dialog adaptation under custom Windows font scaling | Replace with `setMinimumSize(420, 260)` |
| `ui/instructor_view.py` | 61 | `InstructorDialog.setFixedSize(520, 560)` | Hardcoded dialog size restricts layout flexibility | Replace with `setMinimumSize(520, 560)` |
| `ui/leave_application_view.py` | 57 | `ReviewRemarksDialog.setFixedSize(480, 300)` | Hardcoded size | Replace with `setMinimumSize(480, 300)` |
| `ui/leave_management_widget.py` | 56 | `ModifyDatesDialog.setFixedSize(440, 360)` | Hardcoded size | Replace with `setMinimumSize(440, 360)` |
| `ui/leave_rules_view.py` | 55 | `AdjustEntitlementDialog.setFixedSize(440, 280)` | Hardcoded size | Replace with `setMinimumSize(440, 280)` |
| `ui/login_dialog.py` | 47 | `LoginDialog.setFixedSize(520, 620)` | Hardcoded size | Replace with `setMinimumSize(500, 580)` |
| `ui/student_view.py` | 55 | `StudentProfileDialog.setFixedSize(460, 480)` | Hardcoded size prevents responsive card rendering | Replace with `setMinimumSize(460, 480)` |
| `ui/student_view.py` | 128 | `StudentFormDialog.setFixedSize(480, 500)` | Hardcoded size | Replace with `setMinimumSize(480, 500)` |
| `ui/substitute_view.py` | 53 | `SubstituteResponseDialog.setFixedSize(440, 240)` | Hardcoded size | Replace with `setMinimumSize(440, 240)` |
| `ui/biometric_kiosk_window.py` | 159 | `self.resize(1180, 750)` | Initial window size exceeds 768px height (750px + titlebar > 768px screen) | Set initial size to `1080x700` and `setMinimumSize(960, 600)` |
| `ui/login_window.py` | 85 | `self.resize(920, 640)` | Sizing is acceptable; `setMinimumSize(860, 580)` ensures clean fit | Preserve; verified safe for 1366×768 |
| `ui/main_window.py` | 97 | `self.resize(1200, 800)` | Initial height of 800px exceeds 1366×768 screen height | Change initial size to `1200x720` with `setMinimumSize(1024, 640)` |
| `ui/instructor_view.py` | 330, 340 | `layout.addWidget(tbl_instructors); layout.addWidget(empty_state)` | Both table and empty state have `stretch=1`; when switching between empty/populated states, layout needs explicit toggling | Ensure explicit hide/show and solid background styling |
| `ui/student_view.py` | 340, 350 | `layout.addWidget(tbl_students); layout.addWidget(empty_state)` | Both table and empty state added with `stretch=1` | Maintain explicit visibility gating |
| `ui/model_view.py` | 180–230 | `_build_predictor_tab` | Vertical panel with text input, feature inspection, prediction table, and explanation lacks scrollability | Add `QScrollArea` to predictor tab |
| `ui/leave_rules_view.py` | 240–290 | `_build_simulator_tab` | Simulator tab contains stacked forms, results table, and error logs | Add `QScrollArea` to simulator tab |

---

## 4. Verification & Baseline Status

- **Offscreen Execution Mode:** Verified using `$env:QT_QPA_PLATFORM="offscreen"`.
- **Test Suite Results:**
  - Total test files: 29 suites
  - Total tests executed: **197 tests**
  - Failures: **0**
  - Errors: **0**
  - Execution Duration: **82.54 seconds**
- **Conclusion:** Phase 0 audit is complete with zero code modifications made to runtime business logic, database schemas, or ML components.

---
*Awaiting user authorization to proceed to Phase 1 (The Four Known UI Bugs).*
