"""
Constraint Satisfaction Substitute Assignment Solver (CP-SAT & Pure-NumPy Fallback)

Formulates faculty substitute allocation as a formal Constraint Satisfaction Problem (CSP):
- Hard Constraints:
    1. Exactly one substitute per required lecture slot.
    2. Zero timetable schedule collisions (existing lectures or concurrent substitute slots).
    3. Workload cap: Max 2 substitute duties per faculty member per day.
    4. Exclusion of faculty member currently on leave.
- Soft Optimization Objective:
    1. Department continuity bonus (prefer faculty from the same department).
    2. Workload equity (prioritize faculty with fewer accumulated monthly duties).

Execution Mode:
- Primary: Google OR-Tools CP-SAT (if ortools is installed).
- Fallback: Deterministic pure-NumPy heuristic constraint solver (zero runtime external dependencies).
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np

try:
    from ortools.sat.python import cp_model
    ORTOOLS_AVAILABLE = True
except ImportError:
    cp_model = None
    ORTOOLS_AVAILABLE = False


def is_ortools_available() -> bool:
    """Returns True if Google OR-Tools is installed in the current environment."""
    return ORTOOLS_AVAILABLE


def check_time_overlap(start_1: str, end_1: str, start_2: str, end_2: str) -> bool:
    """Checks whether two 'HH:MM:SS' intervals overlap."""
    return max(start_1, start_2) < min(end_1, end_2)


class SubstituteCPSATSolver:
    """
    Intelligent Constraint Satisfaction Solver for institutional substitute allocation.
    """

    def __init__(
        self,
        max_daily_slots: int = 2,
        dept_match_bonus: int = 50,
        base_workload_weight: int = 100,
        workload_penalty_per_duty: int = 10,
    ):
        self.max_daily_slots = max_daily_slots
        self.dept_match_bonus = dept_match_bonus
        self.base_workload_weight = base_workload_weight
        self.workload_penalty_per_duty = workload_penalty_per_duty

    def solve(
        self,
        slots: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
        force_numpy: bool = False,
    ) -> Dict[str, Any]:
        """
        Solves the substitute allocation problem across one or more lecture slots.
        
        Args:
            slots: List of slots to cover. Each dict must include:
                   'slot_id', 'date', 'start_time', 'end_time', 'department_id', 'original_faculty_id'
            candidates: List of candidate faculty. Each dict must include:
                   'faculty_id', 'name', 'department_id', 'monthly_count', 'daily_count', 'busy_slots'
            force_numpy: If True, bypasses OR-Tools even if installed, forcing pure-NumPy solver.

        Returns:
            Dictionary containing assignments, solver status, score, and explanation.
        """
        if not slots:
            return {
                "status": "OPTIMAL",
                "solver": "Empty Problem",
                "assignments": [],
                "unassigned_slots": [],
                "total_score": 0.0,
                "hard_constraints_satisfied": True,
            }

        if not candidates:
            return {
                "status": "INFEASIBLE",
                "solver": "No Candidates",
                "assignments": [],
                "unassigned_slots": [s.get("slot_id") for s in slots],
                "total_score": 0.0,
                "hard_constraints_satisfied": False,
            }

        if ORTOOLS_AVAILABLE and not force_numpy:
            return self._solve_with_cpsat(slots, candidates)
        else:
            return self._solve_with_numpy(slots, candidates)

    def _solve_with_cpsat(
        self,
        slots: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Formulates and solves the assignment problem using Google OR-Tools CP-SAT."""
        model = cp_model.CpModel()
        num_candidates = len(candidates)
        num_slots = len(slots)

        # Decision variables: x[c, s] in {0, 1}
        x = {}
        for c_idx in range(num_candidates):
            for s_idx in range(num_slots):
                x[c_idx, s_idx] = model.NewBoolVar(f"x_{c_idx}_{s_idx}")

        # Hard Constraint 1: Exactly one substitute per slot
        for s_idx in range(num_slots):
            model.Add(sum(x[c_idx, s_idx] for c_idx in range(num_candidates)) == 1)

        # Hard Constraint 2: Original faculty excluded & schedule conflict elimination
        for s_idx, slot in enumerate(slots):
            orig_fac_id = slot.get("original_faculty_id")
            s_date = slot.get("date", "")
            s_start = slot.get("start_time", "09:00:00")
            s_end = slot.get("end_time", "10:00:00")

            for c_idx, cand in enumerate(candidates):
                # Cannot assign original faculty
                if cand.get("faculty_id") == orig_fac_id:
                    model.Add(x[c_idx, s_idx] == 0)
                    continue

                # Pre-existing busy intervals
                busy_intervals = cand.get("busy_slots", [])
                has_external_clash = any(
                    check_time_overlap(s_start, s_end, b_start, b_end)
                    for b_start, b_end in busy_intervals
                )
                if has_external_clash:
                    model.Add(x[c_idx, s_idx] == 0)

        # Hard Constraint 3: No simultaneous overlap across requested slots for same candidate
        for c_idx in range(num_candidates):
            for s1_idx in range(num_slots):
                for s2_idx in range(s1_idx + 1, num_slots):
                    s1 = slots[s1_idx]
                    s2 = slots[s2_idx]
                    if s1.get("date") == s2.get("date"):
                        if check_time_overlap(
                            s1.get("start_time", "09:00:00"),
                            s1.get("end_time", "10:00:00"),
                            s2.get("start_time", "09:00:00"),
                            s2.get("end_time", "10:00:00"),
                        ):
                            # Cannot assign candidate to overlapping slots
                            model.Add(x[c_idx, s1_idx] + x[c_idx, s2_idx] <= 1)

        # Hard Constraint 4: Workload cap (max daily slots per candidate)
        for c_idx, cand in enumerate(candidates):
            existing_daily = cand.get("daily_count", 0)
            remaining_quota = max(0, self.max_daily_slots - existing_daily)
            # Group slots by date
            dates = set(s.get("date", "") for s in slots)
            for d in dates:
                d_slot_indices = [s_idx for s_idx, s in enumerate(slots) if s.get("date", "") == d]
                model.Add(sum(x[c_idx, s_idx] for s_idx in d_slot_indices) <= remaining_quota)

        # Objective Function: Maximize (department match + workload equity)
        objective_terms = []
        for c_idx, cand in enumerate(candidates):
            m_count = cand.get("monthly_count", 0)
            workload_val = max(10, self.base_workload_weight - (m_count * self.workload_penalty_per_duty))

            for s_idx, slot in enumerate(slots):
                same_dept = (cand.get("department_id") == slot.get("department_id"))
                dept_val = self.dept_match_bonus if same_dept else 0
                total_weight = int(workload_val + dept_val)
                objective_terms.append(total_weight * x[c_idx, s_idx])

        model.Maximize(sum(objective_terms))

        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5.0
        status = solver.Solve(model)

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            assignments = []
            total_score = 0.0
            for s_idx, slot in enumerate(slots):
                for c_idx, cand in enumerate(candidates):
                    if solver.Value(x[c_idx, s_idx]) == 1:
                        same_dept = (cand.get("department_id") == slot.get("department_id"))
                        m_count = cand.get("monthly_count", 0)
                        score = (
                            max(10, self.base_workload_weight - (m_count * self.workload_penalty_per_duty))
                            + (self.dept_match_bonus if same_dept else 0)
                        )
                        total_score += score
                        assignments.append({
                            "slot_id": slot.get("slot_id"),
                            "slot_date": slot.get("date"),
                            "slot_time": f"{slot.get('start_time')} - {slot.get('end_time')}",
                            "substitute_id": cand.get("faculty_id"),
                            "substitute_name": cand.get("name"),
                            "department_id": cand.get("department_id"),
                            "same_department": same_dept,
                            "monthly_duties": m_count,
                            "score": float(score),
                            "reason": f"CP-SAT assigned {'same-dept' if same_dept else 'cross-dept'} peer with {m_count} past duties",
                        })
                        break

            return {
                "status": "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE",
                "solver": "Google OR-Tools CP-SAT",
                "assignments": assignments,
                "unassigned_slots": [],
                "total_score": float(total_score),
                "hard_constraints_satisfied": True,
            }
        else:
            # Fallback to NumPy heuristic if CP-SAT proves infeasible under strict caps
            fallback_res = self._solve_with_numpy(slots, candidates)
            fallback_res["solver"] = "Google OR-Tools (Infeasible) -> NumPy Heuristic Fallback"
            return fallback_res

    def _solve_with_numpy(
        self,
        slots: List[Dict[str, Any]],
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Pure-NumPy heuristic constraint solver.
        Builds suitability matrix and executes greedy constrained assignment.
        """
        num_candidates = len(candidates)
        num_slots = len(slots)

        # Feasibility mask [C, S]
        feasibility_mask = np.ones((num_candidates, num_slots), dtype=bool)
        affinity_matrix = np.zeros((num_candidates, num_slots), dtype=np.float64)

        # 1. Evaluate candidate suitability and static conflicts
        for c_idx, cand in enumerate(candidates):
            cand_fac_id = cand.get("faculty_id")
            cand_dept = cand.get("department_id")
            cand_monthly = cand.get("monthly_count", 0)
            cand_daily_base = cand.get("daily_count", 0)
            cand_busy = cand.get("busy_slots", [])

            # Compute candidate base workload score
            base_score = max(10, self.base_workload_weight - (cand_monthly * self.workload_penalty_per_duty))

            for s_idx, slot in enumerate(slots):
                # Hard Constraint: Exclude faculty on leave
                if cand_fac_id == slot.get("original_faculty_id"):
                    feasibility_mask[c_idx, s_idx] = False
                    continue

                # Hard Constraint: Initial daily quota exhausted
                if cand_daily_base >= self.max_daily_slots:
                    feasibility_mask[c_idx, s_idx] = False
                    continue

                # Hard Constraint: Timetable clash with pre-existing busy interval
                s_start = slot.get("start_time", "09:00:00")
                s_end = slot.get("end_time", "10:00:00")
                if any(check_time_overlap(s_start, s_end, b[0], b[1]) for b in cand_busy):
                    feasibility_mask[c_idx, s_idx] = False
                    continue

                # Soft bonus: Same department
                same_dept = (cand_dept == slot.get("department_id"))
                dept_bonus = self.dept_match_bonus if same_dept else 0

                affinity_matrix[c_idx, s_idx] = base_score + dept_bonus

        # Dynamic state tracking
        assigned_daily_counts = {c_idx: candidates[c_idx].get("daily_count", 0) for c_idx in range(num_candidates)}
        assigned_intervals = {c_idx: list(candidates[c_idx].get("busy_slots", [])) for c_idx in range(num_candidates)}

        assignments = []
        unassigned_slots = []
        total_score = 0.0

        # Sort slots by constraint hardness (slots with fewest feasible candidates first)
        candidate_counts = np.sum(feasibility_mask, axis=0)
        slot_order = np.argsort(candidate_counts)

        for s_idx in slot_order:
            slot = slots[s_idx]
            s_start = slot.get("start_time", "09:00:00")
            s_end = slot.get("end_time", "10:00:00")

            # Find feasible candidates for this slot
            feasible_cands = []
            for c_idx in range(num_candidates):
                if not feasibility_mask[c_idx, s_idx]:
                    continue
                # Check daily quota
                if assigned_daily_counts[c_idx] >= self.max_daily_slots:
                    continue
                # Check overlap with already-assigned slots for this candidate
                if any(check_time_overlap(s_start, s_end, b[0], b[1]) for b in assigned_intervals[c_idx]):
                    continue
                feasible_cands.append(c_idx)

            if not feasible_cands:
                unassigned_slots.append(slot.get("slot_id"))
                continue

            # Pick candidate with highest affinity score
            scores = affinity_matrix[feasible_cands, s_idx]
            best_local_idx = np.argmax(scores)
            best_c_idx = feasible_cands[best_local_idx]
            chosen_cand = candidates[best_c_idx]

            # Update dynamic state
            assigned_daily_counts[best_c_idx] += 1
            assigned_intervals[best_c_idx].append((s_start, s_end))

            chosen_score = float(affinity_matrix[best_c_idx, s_idx])
            total_score += chosen_score
            same_dept = (chosen_cand.get("department_id") == slot.get("department_id"))

            assignments.append({
                "slot_id": slot.get("slot_id"),
                "slot_date": slot.get("date"),
                "slot_time": f"{s_start} - {s_end}",
                "substitute_id": chosen_cand.get("faculty_id"),
                "substitute_name": chosen_cand.get("name"),
                "department_id": chosen_cand.get("department_id"),
                "same_department": same_dept,
                "monthly_duties": chosen_cand.get("monthly_count", 0),
                "score": chosen_score,
                "reason": f"NumPy heuristic assigned {'same-dept' if same_dept else 'cross-dept'} peer with {chosen_cand.get('monthly_count', 0)} past duties",
            })

        all_assigned = (len(unassigned_slots) == 0)
        return {
            "status": "OPTIMAL" if all_assigned else ("PARTIAL" if assignments else "INFEASIBLE"),
            "solver": "Pure-NumPy Heuristic (Fallback)",
            "assignments": sorted(assignments, key=lambda a: a["slot_id"]),
            "unassigned_slots": unassigned_slots,
            "total_score": float(total_score),
            "hard_constraints_satisfied": all_assigned,
        }
