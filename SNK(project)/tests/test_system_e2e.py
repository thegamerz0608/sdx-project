"""
Comprehensive End-to-End System Integration Test Suite (Phase 17)
Simulates complete academic ERP workflow:
User Auth -> Faculty Directory -> Attendance Ingestion -> Grace Deduction ->
Leave Submission -> NLP Preprocessing -> TF-IDF Vectorization -> ML Classification ->
AI Risk Recommendation -> HOD Approval -> Substitute Allocation -> PDF/CSV Reports ->
Audit Trail -> System Backup Snapshot.
"""
from pathlib import Path
from services.auth_service import auth_service
from services.department_service import department_service
from services.faculty_service import faculty_service
from imports.attendance_importer import generate_sample_csv
from services.attendance_service import attendance_service
from services.grace_service import grace_service
from services.leave_service import leave_service
from services.leave_workflow_service import leave_workflow_service
from services.nlp_service import nlp_service
from services.tfidf_service import tfidf_service
from services.model_training_service import model_training_service
from services.recommendation_engine import recommendation_engine
from services.substitute_service import substitute_service
from services.report_service import report_service
from services.audit_service import audit_service
from services.backup_service import backup_service


def test_full_erp_end_to_end_workflow(tmp_path):
    """
    Executes a complete 16-step simulated lifecycle through all integrated ERP subsystems.
    """
    # --------------------------------------------------------------------------
    # Step 1: Administrator Authentication
    # --------------------------------------------------------------------------
    admin_session = auth_service.login("admin", "Password@123")
    assert auth_service.is_authenticated()
    assert admin_session.is_authenticated()
    assert admin_session.is_admin()

    # --------------------------------------------------------------------------
    # Step 2: Department and Faculty Directory Lookup
    # --------------------------------------------------------------------------
    depts = department_service.list_departments()
    assert len(depts) >= 1
    mca_dept = depts[0]

    faculty_list = faculty_service.list_faculty(admin_session)
    assert len(faculty_list) >= 2

    # --------------------------------------------------------------------------
    # Step 3: Attendance File Generation & Import
    # --------------------------------------------------------------------------
    csv_file = str(tmp_path / "test_attendance.csv")
    generate_sample_csv(csv_file)
    assert Path(csv_file).exists()

    report = attendance_service.parse_import_file(admin_session, csv_file)
    assert len(report["valid_records"]) > 0

    saved_count = attendance_service.commit_import(admin_session, report["valid_records"])
    assert saved_count > 0

    # --------------------------------------------------------------------------
    # Step 4: Grace Ledger Status Verification
    # --------------------------------------------------------------------------
    grace_status = grace_service.get_faculty_grace_status(faculty_id=2, month_year="2026-10")
    assert grace_status["allowed_minutes"] >= 30
    assert "remaining_minutes" in grace_status

    # --------------------------------------------------------------------------
    # Step 5: Faculty Authentication & Leave Balance Check
    # --------------------------------------------------------------------------
    faculty_session = auth_service.login("fac_rahul", "Password@123")
    assert faculty_session.is_faculty()
    assert faculty_session.faculty_id is not None

    balances = leave_service.get_leave_balances_summary(faculty_session.faculty_id)
    assert len(balances) >= 1

    # --------------------------------------------------------------------------
    # Step 6: Natural Language Leave Reason Analysis
    # --------------------------------------------------------------------------
    free_text_reason = (
        "I am suffering from high fever, acute stomach pain and cold since yesterday, "
        "and doctor advised complete medical bed rest for 2 days."
    )
    tokens = nlp_service.preprocessor.preprocess_text(free_text_reason)
    assert len(tokens) > 0
    assert "fever" in tokens or "pain" in tokens or "rest" in tokens

    # TF-IDF Feature extraction
    tfidf_feat = tfidf_service.extract_features_for_text(free_text_reason)
    assert "tfidf_vector" in tfidf_feat or "clean_text" in tfidf_feat

    # ML Classifier Prediction
    prediction = model_training_service.predict_leave_reason(free_text_reason)
    assert "predicted_type" in prediction
    assert "confidence" in prediction
    assert prediction["confidence"] >= 0.0

    # --------------------------------------------------------------------------
    # Step 7: Leave Application Submission
    # --------------------------------------------------------------------------
    app_result = leave_workflow_service.submit_leave_application(
        user_session=faculty_session,
        requested_type_code="ML",
        from_date="2026-10-15",
        to_date="2026-10-16",
        reason=free_text_reason,
        faculty_selected_type_code="ML",
        document_path="docs/medical_certificate_rahul.pdf",
    )
    assert app_result["success"] is True
    app_code = app_result["application_code"]
    app_id = app_result["application_id"]

    # --------------------------------------------------------------------------
    # Step 8: Multi-Factor AI Risk Recommendation
    # --------------------------------------------------------------------------
    risk_eval = recommendation_engine.evaluate_leave_application(
        faculty_id=faculty_session.faculty_id,
        leave_type_code="ML",
        total_days=2.0,
        from_date="2026-10-15",
        to_date="2026-10-16",
        nlp_predicted_code=prediction["predicted_type"],
        nlp_confidence=prediction["confidence"],
        has_medical_doc=True,
    )
    assert "recommendation" in risk_eval
    assert "risk_score" in risk_eval
    assert 0 <= risk_eval["risk_score"] <= 100

    # --------------------------------------------------------------------------
    # Step 9: HOD Authentication & Review Decision
    # --------------------------------------------------------------------------
    hod_session = auth_service.login("hod_mca", "Password@123")
    assert hod_session.is_hod()

    review_res = leave_workflow_service.review_application(
        user_session=hod_session,
        application_id=app_id,
        action="APPROVE",
        hod_remarks="Approved as per medical reason and AI confidence verification.",
    )
    assert review_res["success"] is True

    # --------------------------------------------------------------------------
    # Step 10: Substitute Faculty Allocation
    # --------------------------------------------------------------------------
    sub_recs = substitute_service.recommend_substitutes(
        department_id=mca_dept["id"],
        original_faculty_id=faculty_session.faculty_id,
        assignment_date="2026-10-15",
        start_time="10:00:00",
        end_time="11:00:00",
    )
    assert isinstance(sub_recs, list)
    assert len(sub_recs) >= 1

    sub_faculty = sub_recs[0]
    assign_res = substitute_service.assign_substitute(
        user_session=hod_session,
        leave_application_id=app_id,
        original_faculty_id=faculty_session.faculty_id,
        substitute_faculty_id=sub_faculty["faculty_id"],
        department_id=mca_dept["id"],
        assignment_date="2026-10-15",
        start_time="10:00:00",
        end_time="11:00:00",
        class_details="MCA-II Big Data Analytics Lecture",
    )
    assert assign_res["success"] is True

    # --------------------------------------------------------------------------
    # Step 11: Institutional Document Generation (PDF & CSV)
    # --------------------------------------------------------------------------
    pdf_path = report_service.generate_pdf_report(
        report_type="ATTENDANCE_SUMMARY",
        department_id=mca_dept["id"],
    )
    assert Path(pdf_path).exists()
    assert Path(pdf_path).stat().st_size > 500

    csv_path = report_service.export_csv_dataset(export_type="ATTENDANCE")
    assert Path(csv_path).exists()
    assert Path(csv_path).stat().st_size > 50

    # --------------------------------------------------------------------------
    # Step 12: Security Audit Verification (Admin Audit Review)
    # --------------------------------------------------------------------------
    auth_service.login("admin", "Password@123")
    audits = audit_service.get_audit_logs(limit=20)
    assert len(audits) >= 5

    # --------------------------------------------------------------------------
    # Step 13: Full System Backup Snapshot
    # --------------------------------------------------------------------------
    backup_res = backup_service.create_backup(backup_name="e2e_verified_state", include_models=True)
    assert backup_res["success"] is True
    assert Path(backup_res["backup_path"]).exists()
    assert backup_res["total_records"] > 0


def test_system_diagnostics_and_rbac_integrity():
    """
    Verifies that system diagnostics, table counts, and RBAC matrix are consistent.
    """
    diag = backup_service.run_system_diagnostics()
    assert diag["total_tables"] == 12
    assert diag["health_status"] in ["HEALTHY", "OPERATIONAL (OFFLINE_FALLBACK)"]

    matrix = audit_service.get_rbac_permission_matrix()
    assert len(matrix) >= 15
    for item in matrix:
        assert "ADMIN" in item and "HOD" in item and "FACULTY" in item
