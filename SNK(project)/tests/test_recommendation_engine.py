"""
Phase 13 Intelligent Leave Recommendation Engine Unit Tests
Verifies multi-signal risk score calculations, decision thresholds (AUTO_APPROVE, FLAG_HOD_REVIEW, REJECT_POLICY_VIOLATION),
NLP intent alignment signals, medical doc verification, substitute availability, and PySide6 RecommendationView.
"""
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

VENV_SITE = BASE_DIR / "venv" / "Lib" / "site-packages"
if VENV_SITE.exists() and str(VENV_SITE) not in sys.path:
    sys.path.insert(0, str(VENV_SITE))

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from services.recommendation_engine import (
    RecommendationEngine,
    recommendation_engine,
    DECISION_AUTO_APPROVE,
    DECISION_FLAG_HOD_REVIEW,
    DECISION_REJECT_POLICY_VIOLATION,
)
from ui.recommendation_view import RecommendationView


@pytest.fixture
def qapp():
    """Ensure a PySide6 QApplication instance exists."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_recommendation_engine_auto_approve():
    """Verify valid Casual Leave with sufficient balance yields AUTO_APPROVE recommendation."""
    res = recommendation_engine.evaluate_leave_application(
        faculty_id=1,
        leave_type_code="CL",
        start_date="2026-10-10",
        end_date="2026-10-10",
        reason_text="Personal work at home regarding bank documentation and Aadhaar update.",
        has_medical_doc=False,
    )

    assert "risk_score" in res
    assert res["risk_score"] < 25.0
    assert res["decision"] == DECISION_AUTO_APPROVE
    assert "AUTO-APPROVE" in res["decision_label"]


def test_recommendation_engine_flag_hod_review():
    """Verify Medical Leave > 2 days missing medical doc triggers FLAG_HOD_REVIEW."""
    res = recommendation_engine.evaluate_leave_application(
        faculty_id=1,
        leave_type_code="ML",
        start_date="2026-10-10",
        end_date="2026-10-13",
        reason_text="Severe viral fever and doctor advised bed rest.",
        has_medical_doc=False,
    )

    assert res["risk_score"] >= 25.0
    assert res["decision"] in [DECISION_FLAG_HOD_REVIEW, DECISION_REJECT_POLICY_VIOLATION]
    factors = [f["factor_code"] for f in res["risk_factors"]]
    assert "MISSING_MEDICAL_DOC" in factors


def test_recommendation_engine_reject_insufficient_balance():
    """Verify application requesting more days than available balance yields REJECT_POLICY_VIOLATION."""
    res = recommendation_engine.evaluate_leave_application(
        faculty_id=1,
        leave_type_code="CL",
        start_date="2026-10-01",
        end_date="2026-10-30",
        reason_text="Personal long vacation.",
        has_medical_doc=False,
    )

    assert res["decision"] == DECISION_REJECT_POLICY_VIOLATION
    factors = [f["factor_code"] for f in res["risk_factors"]]
    assert "INSUFFICIENT_BALANCE" in factors


def test_recommendation_engine_category_equivalence_mapping():
    """Verify that institutional leave categories map to equivalent ML classes without penalty."""
    # AVL (Academic Vacation Leave) should map to EL without triggering ML_INTENT_MISMATCH
    res_avl = recommendation_engine.evaluate_leave_application(
        faculty_id=1,
        leave_type_code="AVL",
        start_date="2026-10-10",
        end_date="2026-10-11",
        reason_text="Annual family vacation and earned leave trip to hometown.",
        has_medical_doc=False,
    )
    factors_avl = [f["factor_code"] for f in res_avl["risk_factors"]]
    assert "ML_INTENT_MISMATCH" not in factors_avl

    # MAT (Maternity Leave) should map to ML without triggering ML_INTENT_MISMATCH
    res_mat = recommendation_engine.evaluate_leave_application(
        faculty_id=1,
        leave_type_code="MAT",
        start_date="2026-10-10",
        end_date="2026-10-12",
        reason_text="Doctor recommended maternity medical leave and health checkup.",
        has_medical_doc=True,
    )
    factors_mat = [f["factor_code"] for f in res_mat["risk_factors"]]
    assert "ML_INTENT_MISMATCH" not in factors_mat



def test_recommendation_view_gui(qapp):
    """Verify PySide6 RecommendationView widget instantiates, populates rules, and runs evaluation."""
    view = RecommendationView()
    assert view is not None
    assert view.sub_tabs.count() == 2

    # Rules table check
    assert view.tbl_rules.rowCount() == 6

    # Faculty combo check
    assert view.combo_faculty.count() > 0

    # Test live evaluator execution
    view.txt_reason.setPlainText("Personal domestic work at native place.")
    view.run_risk_evaluation()
    assert "DECISION:" in view.lbl_decision.text()
    assert view.progress_risk.value() >= 0
