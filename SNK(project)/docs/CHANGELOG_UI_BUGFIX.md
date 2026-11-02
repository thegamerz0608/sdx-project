# UI Overhaul Bugfix & Concurrency Hardening Changelog

**Project:** AI-Enabled Faculty Attendance, Leave and Substitute Management ERP  
**Target Environment:** Windows 10/11 Desktop, PySide6 (Qt 6.7+), MySQL/MariaDB, 1366×768 Standard Resolution  
**Date:** 2026-10-31  
**Baseline Test Execution:** `pytest -q` with `QT_QPA_PLATFORM=offscreen` → **197 passed in 82.54s**  
**Final Test Execution:** `pytest -q` with `QT_QPA_PLATFORM=offscreen` → **242 passed in 36.48s (100% passing)**  
**Version Control Note:** The `git` CLI executable is not installed on the host environment (`where.exe git` returned exit code 1; no `.git` repository folder present). All fixes and regressions are tracked deterministically through explicit audit records, diffs, and change manifests.

---

## 1. Summary of All Addressed Bugs & Root Causes

### Bug 1: Leave Applications "Alternate Arrangement" Group Box Overlapping Fields
- **Symptom:** Substitute Faculty, Duty Date, Time Slot, Location, and Work Description fields visually overlapped and truncated on standard 1366×768 resolution.
- **Root Cause:** The `alt_group` container was constrained by restrictive height policies inside an unscrollable left-column layout; additionally, `txt_alt_work` was a standard single-line `QLineEdit` trying to display multi-line duty descriptions within cramped row spacing.
- **Fix:**
  - In `ui/leave_application_view.py`, wrapped the left form column inside a dedicated `QScrollArea(widgetResizable=True)`.
  - Restructured `alt_group` using a responsive `QFormLayout` (`setLabelAlignment(Qt.AlignLeft)`, `AllNonFixedFieldsGrow`).
  - Converted `txt_alt_work` to a `QPlainTextEdit` with `setMinimumHeight(60)` and added a backward-compatible `.text()` property.
  - Increased table default row height (`tbl_apps.verticalHeader().setDefaultSectionSize(40)`).
- **Files Changed:** `ui/leave_application_view.py`
- **Screenshots:** `docs/screenshots/bugfix/bug1_leave_app_before.png`, `docs/screenshots/bugfix/bug1_leave_app_after.png`

---

### Bug 2: Lab Instructors and Student Directory Background Transparency Tab Bleed
- **Symptom:** Inactive background tabs (Security Audit Trail, RBAC Matrix, Leave Rules) bled into the search bar, filter dropdowns, and table headers of the Lab Instructors and Student Directory views.
- **Root Cause:** Standard PySide6 `QWidget` containers have transparent backgrounds by default. When switched via `QStackedWidget`, underlying pages or root window styling shone through without an explicit background repaint or solid background role.
- **Fix:**
  - In `ui/instructor_view.py` and `ui/student_view.py`, configured `setAttribute(Qt.WA_StyledBackground, True)` and applied explicit solid background stylesheets (`background-color: #F8FAFC;`).
  - In `ui/main_window.py`, styled `QStackedWidget` with solid `#F8FAFC` and triggered `.update()` on the newly activated widget upon each `switch_to_tab()` event.
- **Files Changed:** `ui/instructor_view.py`, `ui/student_view.py`, `ui/main_window.py`
- **Screenshots:** `docs/screenshots/bugfix/bug2_tab_bleed_before.png`, `docs/screenshots/bugfix/bug2_tab_bleed_after.png`

---

### Bug 3: System Dashboard Quick Operational Actions and Table Row Clipping
- **Symptom:** Table rows below the Quick Operational Action buttons clipped into each other, hiding cell text and button badges.
- **Root Cause:** Global QSS rules in `ui/styles.py` applied `9px 12px` padding to `QTableWidget::item` and header sections, which exceeded the default row height for 13px Segoe UI fonts, combined with a fixed dashboard height that lacked vertical scrolling.
- **Fix:**
  - In `ui/styles.py`, reduced table cell and header padding from `9px 12px` to `6px 10px`.
  - In `ui/dashboard_widget.py`, wrapped the entire dashboard content layout in a `QScrollArea(widgetResizable=True)` with smooth scrolling, and set `verticalHeader().setDefaultSectionSize(38)` on dashboard summary tables.
- **Files Changed:** `ui/styles.py`, `ui/dashboard_widget.py`
- **Screenshots:** `docs/screenshots/bugfix/bug3_dashboard_clipped_before.png`, `docs/screenshots/bugfix/bug3_dashboard_clipped_after.png`

---

### Bug 4: Student Profile Modal Stuck on Grey Skeleton
- **Symptom:** Clicking "View Profile" on any row in the Student Directory opened a modal that remained permanently frozen on a grey skeleton placeholder and never rendered student details.
- **Root Cause:** Background database fetching either ran without strong worker thread retention (allowing premature Python garbage collection), swallowed thread exceptions without dispatching to the main thread, or failed to hide the skeleton layout container when data was received.
- **Fix:**
  - In `ui/student_view.py`, refactored `StudentProfileDialog` into three explicit layout states: `skeleton_container`, `content_container`, and `error_container` with a "Retry" button.
  - Offloaded student record queries to a background `WorkerThread` with typed signals (`result`, `error`, `finished`).
  - Ensured UI elements are mutated exclusively within main-thread slots, and bound worker references to prevent GC.
- **Files Changed:** `ui/student_view.py`
- **Tests Added:** `tests/test_student_profile_dialog.py` (2 tests)
- **Screenshots:** `docs/screenshots/bugfix/bug4_student_profile_before.png`, `docs/screenshots/bugfix/bug4_student_profile_after.png`

---

### Bug 5: Biometric Log (CSV) Ingestion Freezing the Main UI
- **Symptom:** Importing or validating biometric attendance CSVs froze the PySide6 UI; duplicate clicks spawned concurrent race conditions; unparented worker threads risked crashes on window disposal.
- **Root Cause:** Missing loading modal overlay allowed repeated button clicks; parsing was not shielded by UI busy states; background threads were loosely bound without cancellation on window `closeEvent`.
- **Fix:**
  - In `ui/attendance_view.py`, mounted `LoadingOverlay(self)` tracking parent geometry via `eventFilter`.
  - Updated `_do_parse_async` and `_do_commit_async` to disable buttons, activate `LoadingOverlay`, dispatch via `WorkerThread`, and handle errors with an explicit Retry callback.
  - Implemented `closeEvent` to stop active background workers cleanly.
- **Files Changed:** `ui/attendance_view.py`, `ui/worker.py`
- **Tests Added:** `tests/test_functional_threading_fixes.py::test_attendance_view_overlay_and_async_parsing`

---

### Bug 6: NLP Leave Classifier Error on Short, Empty, or None Input
- **Symptom:** Calling `predict_leave_reason(None)` or entering short/empty inputs crashed with `AttributeError: 'NoneType' object has no attribute 'split'`.
- **Root Cause:** In `nlp/oov_detector.py`, `assess_input_vocabulary` invoked `raw_text.split()` without checking if `raw_text` was `None` or a non-string object.
- **Fix:**
  - In `nlp/oov_detector.py`, added strict guards against `None`, empty, and non-string inputs in `is_gibberish_string` and `assess_input_vocabulary`, returning `unknown_tokens: []` safely.
  - In `services/model_training_service.py`, sanitized `raw_text = str(raw_text or "").strip()`.
  - In `ui/leave_application_view.py`, updated live debounced NLP feedback to display an amber out-of-vocabulary warning badge when `is_oov` is flagged.
- **Files Changed:** `nlp/oov_detector.py`, `services/model_training_service.py`, `ui/leave_application_view.py`
- **Tests Added:** `tests/test_functional_threading_fixes.py::test_nlp_classifier_handles_short_empty_none_gracefully` (10 parameterized edge cases), `test_nlp_classifier_valid_input_high_confidence`

---

### Bug 7: Substitute Engine Candidate Filtering & Responsiveness
- **Symptom:** Requesting faculty was recommended as their own substitute; System Admin accounts appeared as teaching substitutes; clicking "Find Eligible Substitutes" froze the UI.
- **Root Cause:** Type mismatch in `fac_id == original_faculty_id` (`2 == '2'` -> `False`) failed to exclude faculty when IDs were passed as strings; lack of non-teaching role filtering; synchronous database queries on the main thread in `SubstituteView`.
- **Fix:**
  - In `services/substitute_service.py`, normalized ID comparisons with `int(fac_id) == orig_fac_norm` and excluded accounts where `role == 'ADMIN'`, `designation == 'System Administrator'`, or `status == 'INACTIVE'`.
  - In `ui/substitute_view.py`, mounted `LoadingOverlay(self)`, offloaded candidate recommendation to a background `WorkerThread`, disabled the search button during execution, rendered results in a main-thread slot, and added `closeEvent` teardown.
- **Files Changed:** `services/substitute_service.py`, `ui/substitute_view.py`
- **Tests Added:** `tests/test_functional_threading_fixes.py::test_substitute_excludes_original_faculty_integer`, `test_substitute_excludes_original_faculty_string`, `test_substitute_excludes_system_admin_role`, `test_substitute_view_search_non_blocking`

---

### Bug 8: Concurrency Architecture & Qt `moveToThread` Refactoring
- **Symptom:** Subclassing `QThread` and overriding `run()` created threading pitfalls where thread lifecycle slots were misrouted to creating threads.
- **Root Cause:** Standard Qt anti-pattern of subclassing `QThread` rather than utilizing the recommended `QObject.moveToThread()` worker pattern.
- **Fix:**
  - In `ui/worker.py`, implemented `WorkerObject(QObject)` + `WorkerThread(QObject)` adhering strictly to `moveToThread`.
  - Wired lifecycle so worker tasks run inside the worker thread, emit typed signals (`progress`, `result`, `error`, `finished`), call `QThread.currentThread().quit()` upon completion, and clean up safely via `deleteLater()`.
  - Enhanced `LoadingOverlay` with parent resize tracking via `eventFilter`, indeterminate loading state, and error/retry views.
  - Implemented `closeEvent` cleanup across `AttendanceView`, `SubstituteView`, `BackupView`, `ReportView`, and `ModelView`.
- **Files Changed:** `ui/worker.py`, `ui/backup_view.py`, `ui/report_view.py`, `ui/model_view.py`
- **Tests Added:** `tests/test_functional_threading_fixes.py::test_worker_object_movetothread_success`, `test_worker_object_movetothread_error_handling`, `test_worker_object_cancellation`

---

## 2. Global Layout Standardizations (1366×768 Resolution Support)

1. **Replaced Fixed Sizes with Minimum Sizes:**
   Replaced rigid `setFixedSize` calls with responsive `setMinimumSize` across all modal dialogs to allow proper layout adaptation on high-DPI Windows displays:
   - `DepartmentDialog`: 420×320
   - `FacultyDialog`: 500×540
   - `AdjustAllowanceDialog`: 420×260
   - `InstructorDialog`: 520×560
   - `ReviewRemarksDialog`: 480×300
   - `ModifyDatesDialog`: 440×360
   - `AdjustEntitlementDialog`: 440×280
   - `LoginDialog`: 500×580
   - `SubstituteResponseDialog`: 440×240
   - `MainWindow`: initial 1200×720 (`setMinimumSize(1024, 640)`)
   - `BiometricKioskWindow`: initial 1120×680 (`setMinimumSize(960, 600)`)

2. **Dense View Scroll Areas & Tab Overflow:**
   - Wrapped dense tab pages in `QScrollArea(widgetResizable=True)`: `ModelView.tab_predictor`, `LeaveRulesView.tab_simulator`, `ReportView.tab_pdf`.
   - Enabled `setUsesScrollButtons(True)` and `setElideMode(Qt.ElideRight)` on tab bars.

3. **Data Table Policies & Row Heights:**
   - Applied `setSizePolicy(Expanding, Expanding)` and `setAlternatingRowColors(True)` across all 22 main data tables.
   - Enforced `verticalHeader().setDefaultSectionSize(...) >= 36px` to prevent cell clipping.

4. **Legitimate setGeometry Exceptions:**
   - Toast notifications and modal loading overlays (`LoadingOverlay`) that track parent geometry via `eventFilter` or `resizeEvent`.
   - Custom QR code drawing in biometric kiosk components.

---

## 3. Test Suite Metrics & Verification

All automated tests were executed using `pytest -q` with `$env:QT_QPA_PLATFORM="offscreen"`:

| Stage | Passing Tests | Execution Time | New Suites Introduced |
| :--- | :--- | :--- | :--- |
| **Baseline (Phase 0)** | 197 | 82.54s | Baseline suite |
| **Phase 1 (Known Bugs)** | 199 | 34.12s | `tests/test_student_profile_dialog.py` (+2 tests) |
| **Phase 2 (Global Layouts)** | 223 | 32.60s | `tests/test_layout_sanity_1366x768.py` (+24 tests) |
| **Phase 3 (Functional Fixes)** | 242 | 46.36s | `tests/test_functional_threading_fixes.py` (+19 tests) |
| **Final Verification (Phase 4)** | **242** | **36.48s** | **All 242 tests passing (100% pass rate)** |

### Verified Test Suites Breakdown:
- `tests/test_foundation.py`
- `tests/test_database.py`
- `tests/test_security_auth.py`
- `tests/test_faculty_department.py`
- `tests/test_attendance.py`
- `tests/test_grace_period.py`
- `tests/test_leave_rules.py`
- `tests/test_leave_workflow.py`
- `tests/test_substitute.py`
- `tests/test_nlp_dataset.py`
- `tests/test_ml_tfidf.py`
- `tests/test_ml_classifiers.py`
- `tests/test_recommendation.py`
- `tests/test_analytics.py`
- `tests/test_reports.py`
- `tests/test_audit_security.py`
- `tests/test_backup_restore.py`
- `tests/test_biometric_kiosk.py`
- `tests/test_web_portal.py`
- `tests/test_system_e2e.py`
- `tests/test_ml_calibration_and_oov.py`
- `tests/test_v3_upgrades.py`
- `tests/test_ui_enterprise_polish.py`
- `tests/test_student_profile_dialog.py` (Added in Phase 1)
- `tests/test_layout_sanity_1366x768.py` (Added in Phase 2)
- `tests/test_functional_threading_fixes.py` (Added in Phase 3)

---

## 4. Manual Verification Checklist (Real Windows Hardware Testing)

The following checklist specifies physical hardware and display configurations that should be manually verified on an interactive Windows desktop:

1. **High-DPI Display Scaling (125% & 150%):**
   - [ ] Navigate to **Windows Settings → System → Display → Scale & layout**.
   - [ ] Set scale to **125%** on a 1920×1080 display. Launch `python main.py`. Verify that modal dialogs (`FacultyDialog`, `DepartmentDialog`, `InstructorDialog`) open without cut-off button rows or obscured input fields.
   - [ ] Set scale to **150%** (standard on high-DPI laptops). Open the **Leave Applications** view and ensure the left-hand scroll area allows reaching the "Submit Application" button.
   - [ ] Verify that table row heights remain >= 36px and badge text does not clip.

2. **Touch Screen & Tablet Mode Interactions:**
   - [ ] Test vertical flick scrolling on `DashboardWidget`, `LeaveApplicationView`, and `ReportView` scroll areas.
   - [ ] Verify that combo box tap targets (`QComboBox`) and table action buttons have sufficient tap surface area.
   - [ ] Open the Biometric Kiosk window (`python ui/biometric_kiosk_window.py`) and verify that on-screen keypad buttons trigger on touch.

3. **Multi-Monitor & DPI Transition (Per-Monitor V2):**
   - [ ] Connect a secondary display with differing DPI scaling (e.g., 1080p at 100% and 4K at 175%).
   - [ ] Drag the `MainWindow` across the boundary between monitors.
   - [ ] Verify that fonts, card borders, and `LoadingOverlay` reposition smoothly without residual visual artifacts or window clipping.

4. **Window State Transitions:**
   - [ ] Start application in default size (1200×720). Maximize the window (`Win + Up Arrow`). Verify that all tables stretch cleanly across available width.
   - [ ] Restore down (`Win + Down Arrow`) and resize to minimum boundary (1024×640). Verify that horizontal scroll bars or layout managers adapt without overlapping labels.
