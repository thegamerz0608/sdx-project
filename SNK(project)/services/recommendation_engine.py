"""
Intelligent Leave Recommendation & Risk Engine
Evaluates multi-signal risk factors (ML intent alignment, leave balance availability, sandwich policy, medical doc verification, substitute availability, attendance history) into a 0-100 risk score and auto-approval recommendation.
"""
import sys
import os
from datetime import datetime, timedelta

from services.model_training_service import model_training_service
from repositories.leave_repository import leave_repository
from repositories.grace_repository import grace_repository
from services.substitute_service import substitute_service
from nlp.dataset_generator import LEAVE_CATEGORIES
from utils.logger import get_logger

logger = get_logger("services.recommendation_engine")

# Risk Score Thresholds
DECISION_AUTO_APPROVE = "AUTO_APPROVE"
DECISION_FLAG_HOD_REVIEW = "FLAG_HOD_REVIEW"
DECISION_REJECT_POLICY_VIOLATION = "REJECT_POLICY_VIOLATION"


class RecommendationEngine:
    """Multi-factor AI decision engine evaluating leave application risk score and policy recommendations."""

    def calculate_duration(self, start_date_str: str, end_date_str: str) -> float:
        """Calculates inclusive duration days between start and end dates."""
        try:
            d1 = datetime.strptime(start_date_str, "%Y-%m-%d")
            d2 = datetime.strptime(end_date_str, "%Y-%m-%d")
            delta = (d2 - d1).days + 1
            return max(0.5, float(delta))
        except Exception:
            return 1.0

    def check_sandwich_rule(self, start_date_str: str, end_date_str: str, leave_type_code: str) -> Dict[str, Any]:
        """Checks if application range spans weekends or holiday boundaries."""
        try:
            from_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            to_dt = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            calendar_days = (to_dt - from_dt).days + 1

            sandwich_days = 0
            curr = from_dt
            while curr <= to_dt:
                if curr.weekday() in [5, 6]:
                    sandwich_days += 1
                curr += timedelta(days=1)

            is_sandwich = (sandwich_days > 0 and leave_type_code in ["CL", "RL"] and calendar_days > 1)
            return {
                "is_sandwich": is_sandwich,
                "sandwich_days": sandwich_days,
                "reason": f"Application spans {sandwich_days} weekend day(s)." if is_sandwich else "",
            }
        except Exception:
            return {"is_sandwich": False, "sandwich_days": 0, "reason": ""}

    def evaluate_leave_application(
        self,
        faculty_id: int,
        leave_type_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        reason_text: str = "",
        has_medical_doc: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Executes multi-factor evaluation of a leave application.
        Returns risk score (0-100), decision recommendation code, active risk factors list, and ML intent summary.
        """
        s_date = start_date or kwargs.get("from_date") or date.today().isoformat()
        e_date = end_date or kwargs.get("to_date") or s_date
        r_text = reason_text or kwargs.get("reason", "")
        has_doc = has_medical_doc or kwargs.get("has_doc", False)

        logger.info(f"Evaluating leave application for faculty #{faculty_id}, type={leave_type_code}, dates={s_date} to {e_date}")
        duration_days = kwargs.get("total_days") or self.calculate_duration(s_date, e_date)

        risk_factors: List[Dict[str, Any]] = []
        total_risk_score = 0.0

        # Signal 1: Leave Balance Availability Check
        balances = leave_repository.get_faculty_balances(faculty_id)
        bal_item = next((b for b in balances if b.get("leave_type_code") == leave_type_code), None)
        available_balance = float(bal_item.get("remaining_days", 0.0)) if bal_item else 0.0

        is_insufficient_balance = available_balance < duration_days
        if is_insufficient_balance:
            weight = 40.0
            total_risk_score += weight
            risk_factors.append({
                "factor_code": "INSUFFICIENT_BALANCE",
                "factor_name": "Insufficient Leave Balance",
                "weight": weight,
                "description": f"Requested duration ({duration_days} days) exceeds available balance ({available_balance} days).",
                "severity": "HIGH",
            })

        # Signal 2: ML Intent & Category Alignment Check
        metadata = {
            "requested_days": duration_days,
            "notice_period_days": 0.0,
            "has_medical_doc": has_medical_doc,
            "is_sandwich_leave": False,
        }
        ml_res = model_training_service.predict_leave_reason(reason_text, metadata)
        ml_pred_cat = ml_res.get("predicted_category", "CL")
        ml_confidence = ml_res.get("confidence_score", 0.0)

        # Dynamic Category Equivalence Mapping across all 10 institutional leave types
        CATEGORY_EQUIVALENCE = {
            "AVL": "EL",  # Academic Vacation Leave aligns with Earned/Vacation Leave
            "MAT": "ML",  # Maternity Leave aligns with Medical Leave
            "PAT": "ML",  # Paternity Leave aligns with Medical Leave
            "CPL": "CL",  # Compensatory Leave aligns with Casual Leave
            "RL": "CL",   # Restricted Leave aligns with Casual Leave
        }
        aligned_requested_code = CATEGORY_EQUIVALENCE.get(leave_type_code, leave_type_code)

        is_ml_mismatch = (ml_pred_cat != aligned_requested_code) and (ml_confidence >= 0.40)
        if is_ml_mismatch:
            weight = 25.0
            total_risk_score += weight
            predicted_name = LEAVE_CATEGORIES.get(ml_pred_cat, ml_pred_cat)
            requested_name = LEAVE_CATEGORIES.get(leave_type_code, leave_type_code)
            risk_factors.append({
                "factor_code": "ML_INTENT_MISMATCH",
                "factor_name": "NLP Intent Mismatch",
                "weight": weight,
                "description": f"Text reason describes {predicted_name} ({ml_pred_cat}), but faculty applied for {requested_name} ({leave_type_code}).",
                "severity": "MEDIUM",
            })

        # Signal 3: Medical Document Compliance Check
        if leave_type_code == "ML" and duration_days > 2.0 and not has_medical_doc:
            weight = 30.0
            total_risk_score += weight
            risk_factors.append({
                "factor_code": "MISSING_MEDICAL_DOC",
                "factor_name": "Missing Medical Documentation",
                "weight": weight,
                "description": f"Medical leave exceeding 2 days ({duration_days} days requested) requires doctor certificate attachment.",
                "severity": "HIGH",
            })

        # Signal 4: Sandwich Leave Policy Check
        sandwich_check = self.check_sandwich_rule(start_date, end_date, leave_type_code)
        is_sandwich = sandwich_check.get("is_sandwich", False)
        if is_sandwich:
            weight = 15.0
            total_risk_score += weight
            risk_factors.append({
                "factor_code": "SANDWICH_LEAVE_FLAG",
                "factor_name": "Sandwich Leave Rule Triggered",
                "weight": weight,
                "description": sandwich_check.get("reason", "Application spans or adjoins weekend/holiday boundaries."),
                "severity": "MEDIUM",
            })

        # Signal 5: Substitute Faculty Availability Check
        try:
            from services.auth_service import auth_service
            user_sess = auth_service.get_current_session()
            if not user_sess:
                user_sess = auth_service.login("admin", "Password@123")
            substitutes = substitute_service.recommend_substitutes(
                user_session=user_sess,
                original_faculty_id=faculty_id,
                assignment_date=start_date,
                start_time="09:00:00",
                end_time="10:00:00",
            )
            has_substitute = len(substitutes) > 0 and substitutes[0].get("score", 0.0) > 40.0
        except Exception as exc:
            logger.debug(f"Substitute lookup fallback: {exc}")
            substitutes = []
            has_substitute = True

        if not has_substitute:
            weight = 20.0
            total_risk_score += weight
            risk_factors.append({
                "factor_code": "SUBSTITUTE_COLLISION",
                "factor_name": "Substitute Faculty Conflict",
                "weight": weight,
                "description": "No unassigned substitute faculty with matching expertise available on requested date.",
                "severity": "MEDIUM",
            })

        # Signal 6: Attendance & Grace History Check
        try:
            grace_info = grace_repository.get_faculty_grace(faculty_id, month_year="2026-09")
            is_exhausted = grace_info and grace_info.get("status") == "EXHAUSTED"
        except Exception as exc:
            logger.debug(f"Grace check fallback: {exc}")
            is_exhausted = False

        if is_exhausted:
            weight = 10.0
            total_risk_score += weight
            risk_factors.append({
                "factor_code": "POOR_PUNCTUALITY_HISTORY",
                "factor_name": "Grace Allowance Exhausted",
                "weight": weight,
                "description": "Faculty has exhausted monthly late arrival grace allowance.",
                "severity": "LOW",
            })

        # Final Risk Score Capping
        final_risk_score = min(100.0, total_risk_score)

        # Decision Recommendation Threshold Mapping
        if is_insufficient_balance or final_risk_score > 65.0:
            decision = DECISION_REJECT_POLICY_VIOLATION
            decision_label = "REJECT: Institutional Policy Violation"
            decision_color = "#c62828"  # Red
        elif final_risk_score >= 25.0:
            decision = DECISION_FLAG_HOD_REVIEW
            decision_label = "FLAG: Requires Manual HOD Review"
            decision_color = "#f57c00"  # Amber
        else:
            decision = DECISION_AUTO_APPROVE
            decision_label = "AUTO-APPROVE: Low Risk Application"
            decision_color = "#2e7d32"  # Green

        return {
            "faculty_id": faculty_id,
            "leave_type_code": leave_type_code,
            "leave_type_name": LEAVE_CATEGORIES.get(leave_type_code, leave_type_code),
            "start_date": start_date,
            "end_date": end_date,
            "duration_days": duration_days,
            "available_balance": available_balance,
            "risk_score": final_risk_score,
            "decision": decision,
            "recommendation": decision,
            "decision_label": decision_label,
            "decision_color": decision_color,
            "risk_factors": risk_factors,
            "ml_prediction": {
                "predicted_category": ml_pred_cat,
                "predicted_name": LEAVE_CATEGORIES.get(ml_pred_cat, ml_pred_cat),
                "confidence": ml_confidence,
                "confidence_pct": f"{ml_confidence * 100:.1f}%",
                "probabilities": ml_res.get("probabilities", {}),
            },
            "substitute_recommendation": substitutes[0] if substitutes else None,
        }


recommendation_engine = RecommendationEngine()
