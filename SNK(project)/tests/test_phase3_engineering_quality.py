"""
Unit and Integration Tests for Phase 3: Engineering Quality & System Robustness

Verifies:
1. Kiosk Real-Time Feed (SSE Stream & Polling Buffer)
2. Constraint Satisfaction Substitute Solver (CP-SAT & Pure-NumPy Fallback)
3. Performance Benchmark Integrity & SLAs
"""

import sys
import json
import asyncio
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.mobile_punch_service import (
    create_mobile_app,
    broadcast_kiosk_punch,
    _recent_kiosk_punches,
    _kiosk_subscribers,
)
from services.substitute_cpsat_solver import (
    SubstituteCPSATSolver,
    check_time_overlap,
    is_ortools_available,
)


# ==============================================================================
# 1. KIOSK STREAM & POLLING BUFFER TESTS
# ==============================================================================

def test_kiosk_broadcast_and_recent_buffer():
    """Verify broadcast_kiosk_punch updates buffer and delivers to active subscriber queues."""
    test_punch = {
        "employee_code": "TEST01",
        "full_name": "Test Faculty",
        "department": "MCA",
        "punch_type": "CHECK_IN",
        "punch_time": "09:05:00",
        "status": "PRESENT",
    }

    # Setup simulated subscriber queue
    sub_queue = asyncio.Queue()
    _kiosk_subscribers.add(sub_queue)

    try:
        broadcast_kiosk_punch(test_punch)

        # Buffer update verification
        assert len(_recent_kiosk_punches) > 0
        assert _recent_kiosk_punches[-1]["employee_code"] == "TEST01"

        # Queue message delivery verification
        assert not sub_queue.empty()
        delivered = sub_queue.get_nowait()
        assert delivered["employee_code"] == "TEST01"
        assert delivered["punch_type"] == "CHECK_IN"
    finally:
        _kiosk_subscribers.discard(sub_queue)


def test_kiosk_endpoints_registered_on_fastapi():
    """Verify /api/kiosk/stream and /api/kiosk/recent are registered routes."""
    app = create_mobile_app()
    routes = [r.path for r in app.routes]
    assert "/api/kiosk/stream" in routes
    assert "/api/kiosk/recent" in routes


# ==============================================================================
# 2. CONSTRAINT SATISFACTION SUBSTITUTE SOLVER TESTS
# ==============================================================================

def test_time_overlap_logic():
    """Verify interval overlap utility."""
    assert check_time_overlap("09:00:00", "10:00:00", "09:30:00", "10:30:00") is True
    assert check_time_overlap("09:00:00", "10:00:00", "10:00:00", "11:00:00") is False
    assert check_time_overlap("11:00:00", "12:00:00", "09:00:00", "10:00:00") is False


def test_substitute_solver_initialization():
    """Verify solver instantiates with configurable weights."""
    solver = SubstituteCPSATSolver(max_daily_slots=2, dept_match_bonus=50)
    assert solver.max_daily_slots == 2
    assert solver.dept_match_bonus == 50
    assert isinstance(is_ortools_available(), bool)


def test_substitute_solver_excludes_original_faculty():
    """Verify faculty member on leave cannot be assigned to their own slot."""
    solver = SubstituteCPSATSolver()
    slots = [{
        "slot_id": "SLOT_1",
        "date": "2026-10-30",
        "start_time": "10:00:00",
        "end_time": "11:00:00",
        "department_id": 1,
        "original_faculty_id": 101,
    }]
    candidates = [
        {"faculty_id": 101, "name": "Faculty On Leave", "department_id": 1, "monthly_count": 0, "daily_count": 0, "busy_slots": []},
        {"faculty_id": 102, "name": "Available Peer", "department_id": 1, "monthly_count": 0, "daily_count": 0, "busy_slots": []},
    ]

    res = solver.solve(slots, candidates)
    assert res["status"] in ["OPTIMAL", "FEASIBLE"]
    assert len(res["assignments"]) == 1
    assert res["assignments"][0]["substitute_id"] == 102
    assert res["hard_constraints_satisfied"] is True


def test_substitute_solver_timetable_clash_rejection():
    """Verify candidates with overlapping commitments are not assigned."""
    solver = SubstituteCPSATSolver()
    slots = [{
        "slot_id": "SLOT_1",
        "date": "2026-10-30",
        "start_time": "10:00:00",
        "end_time": "11:00:00",
        "department_id": 1,
        "original_faculty_id": 999,
    }]
    candidates = [
        # Candidate 1 has a lecture 10:30 - 11:30 (overlaps)
        {"faculty_id": 201, "name": "Busy Faculty", "department_id": 1, "monthly_count": 0, "daily_count": 0, "busy_slots": [("10:30:00", "11:30:00")]},
        # Candidate 2 is completely free
        {"faculty_id": 202, "name": "Free Faculty", "department_id": 1, "monthly_count": 0, "daily_count": 0, "busy_slots": []},
    ]

    res = solver.solve(slots, candidates)
    assert len(res["assignments"]) == 1
    assert res["assignments"][0]["substitute_id"] == 202


def test_substitute_solver_daily_workload_cap():
    """Verify candidate with maxed daily quota cannot receive additional duties."""
    solver = SubstituteCPSATSolver(max_daily_slots=2)
    slots = [{
        "slot_id": "SLOT_1",
        "date": "2026-10-30",
        "start_time": "14:00:00",
        "end_time": "15:00:00",
        "department_id": 1,
        "original_faculty_id": 999,
    }]
    candidates = [
        # Candidate 1 already did 2 substitute duties today
        {"faculty_id": 301, "name": "Maxed Faculty", "department_id": 1, "monthly_count": 0, "daily_count": 2, "busy_slots": []},
        # Candidate 2 did 0 duties
        {"faculty_id": 302, "name": "Fresh Faculty", "department_id": 1, "monthly_count": 0, "daily_count": 0, "busy_slots": []},
    ]

    res = solver.solve(slots, candidates)
    assert len(res["assignments"]) == 1
    assert res["assignments"][0]["substitute_id"] == 302


def test_substitute_solver_department_priority():
    """Verify same-department peer is preferred over cross-department when both free."""
    solver = SubstituteCPSATSolver(dept_match_bonus=50)
    slots = [{
        "slot_id": "SLOT_1",
        "date": "2026-10-30",
        "start_time": "11:00:00",
        "end_time": "12:00:00",
        "department_id": 1,  # MCA
        "original_faculty_id": 999,
    }]
    candidates = [
        {"faculty_id": 401, "name": "Civil Peer", "department_id": 2, "monthly_count": 0, "daily_count": 0, "busy_slots": []},
        {"faculty_id": 402, "name": "MCA Peer", "department_id": 1, "monthly_count": 0, "daily_count": 0, "busy_slots": []},
    ]

    res = solver.solve(slots, candidates)
    assert res["assignments"][0]["substitute_id"] == 402
    assert res["assignments"][0]["same_department"] is True


def test_substitute_solver_batch_multi_slots():
    """Verify solver handles multiple slots and enforces daily quota across the batch."""
    solver = SubstituteCPSATSolver(max_daily_slots=2)
    slots = [
        {"slot_id": "S1", "date": "2026-10-30", "start_time": "09:00:00", "end_time": "10:00:00", "department_id": 1, "original_faculty_id": 999},
        {"slot_id": "S2", "date": "2026-10-30", "start_time": "10:00:00", "end_time": "11:00:00", "department_id": 1, "original_faculty_id": 999},
        {"slot_id": "S3", "date": "2026-10-30", "start_time": "11:00:00", "end_time": "12:00:00", "department_id": 1, "original_faculty_id": 999},
    ]
    candidates = [
        {"faculty_id": 501, "name": "Faculty Alpha", "department_id": 1, "monthly_count": 0, "daily_count": 0, "busy_slots": []},
        {"faculty_id": 502, "name": "Faculty Beta", "department_id": 1, "monthly_count": 0, "daily_count": 0, "busy_slots": []},
    ]

    res = solver.solve(slots, candidates)
    assert len(res["assignments"]) == 3
    assert res["hard_constraints_satisfied"] is True

    # Check that neither candidate was given > 2 slots
    assigned_ids = [a["substitute_id"] for a in res["assignments"]]
    assert assigned_ids.count(501) <= 2
    assert assigned_ids.count(502) <= 2


# ==============================================================================
# 3. PERFORMANCE RESULTS INTEGRITY TEST
# ==============================================================================

def test_performance_benchmark_results_file():
    """Verify docs/performance_results.json exists and meets institutional SLAs."""
    perf_file = BASE_DIR / "docs" / "performance_results.json"
    assert perf_file.exists(), "Performance results JSON file must be generated by benchmark"

    with open(perf_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_requests"] >= 1000
    assert data["success_rate_pct"] == 100.0
    assert data["rps"] > 500.0
    assert data["overall_latency_ms"]["mean"] < 50.0
    assert data["overall_latency_ms"]["p50"] < 10.0
    assert data["overall_latency_ms"]["p95"] < 100.0


# ==============================================================================
# 4. EDGE CASE & MODULE COVERAGE BOOST TESTS
# ==============================================================================

def test_substitute_solver_edge_cases():
    """Verify solver handles empty problem, empty candidate pool, and forced numpy."""
    solver = SubstituteCPSATSolver()

    # Empty slots
    res_empty = solver.solve([], [{"faculty_id": 1, "name": "A"}])
    assert res_empty["status"] == "OPTIMAL"
    assert len(res_empty["assignments"]) == 0

    # No candidates
    res_no_cand = solver.solve([{"slot_id": "S1"}], [])
    assert res_no_cand["status"] == "INFEASIBLE"
    assert res_no_cand["hard_constraints_satisfied"] is False

    # Force pure-numpy execution
    slots = [{"slot_id": 1, "date": "2026-10-30", "start_time": "10:00:00", "end_time": "11:00:00", "department_id": 1, "original_faculty_id": 99}]
    cands = [{"faculty_id": 2, "name": "B", "department_id": 1, "monthly_count": 0, "daily_count": 0, "busy_slots": []}]
    res_np = solver.solve(slots, cands, force_numpy=True)
    assert res_np["status"] == "OPTIMAL"
    assert res_np["solver"] == "Pure-NumPy Heuristic (Fallback)"


def test_explain_model_features_with_weight_matrix():
    """Verify explain_model_features extracts top positive and negative features from linear W matrix."""
    import numpy as np
    from nlp.explainability import explain_model_features

    class MockLinearModel:
        def __init__(self):
            # 10 features, 5 classes
            self.W = np.array([
                [2.5, -1.0, 0.2, 0.5, -0.8],
                [-1.5, 3.0, -0.4, 0.1, 0.2],
                [0.8, -0.5, 2.1, -1.2, 0.0],
                [1.2, 0.3, -0.9, 1.8, -0.5],
                [-0.4, -0.2, 0.5, -0.3, 1.9],
            ])

    features = ["fever", "exam", "wedding", "conference", "childcare"]
    res = explain_model_features(MockLinearModel(), features, top_k=2)
    assert isinstance(res, dict)
    assert "CL" in res and "ML" in res
    assert "positive_features" in res["CL"]
    assert "negative_features" in res["CL"]
    assert len(res["CL"]["positive_features"]) <= 2


def test_time_service_temporal_context_and_mode_toggle():
    """Verify TimeService test mode toggle, datetime overrides, and reset."""
    from datetime import datetime
    from services.time_service import TimeService

    # Set in-memory test time
    fixed_dt = datetime(2026, 12, 25, 10, 30, 0)
    TimeService.set_in_memory_override(fixed_dt)
    assert TimeService.get_current_time() == fixed_dt
    assert TimeService.get_current_date() == fixed_dt.date()

    # Reset to normal mode
    TimeService.set_in_memory_override(None)
    assert abs((TimeService.get_current_time() - datetime.now()).total_seconds()) < 2.0


def test_public_tunnel_manager_utilities():
    """Verify public_tunnel_manager helper functions."""
    from services.public_tunnel_manager import (
        kill_process_tree,
        cleanup_tunnel,
    )

    # Safe no-op call on None
    kill_process_tree(None)
    cleanup_tunnel()
