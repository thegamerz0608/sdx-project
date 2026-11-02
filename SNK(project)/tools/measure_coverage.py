"""
Statement Coverage Measurement Tool (Pure Python Standard Library)

Measures executable statement coverage across all non-GUI ERP core packages:
- nlp/
- services/
- repositories/
- utils/
- models/

Uses Python's ast (Abstract Syntax Tree) to extract true executable statement lines,
and sys.settrace() to record live executed line numbers during test suite execution.
Generates tabular console output and exports docs/coverage_summary.json and docs/COVERAGE.md.
"""

import sys
import os
import ast
import json
import time
from pathlib import Path
from typing import Dict, Set, List, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TARGET_DIRS = ["nlp", "services", "repositories", "utils", "models"]


def find_target_python_files() -> Dict[str, Path]:
    """Finds all target Python source files across non-GUI modules."""
    py_files = {}
    for d in TARGET_DIRS:
        dir_path = PROJECT_ROOT / d
        if not dir_path.exists():
            continue
        for p in dir_path.rglob("*.py"):
            if "__pycache__" in str(p) or p.name.startswith("test_"):
                continue
            # Store normalized absolute path as key
            py_files[str(p.resolve()).lower()] = p
    return py_files


def extract_executable_statement_lines(file_path: Path) -> Set[int]:
    """
    Parses Python source using AST to identify line numbers of all executable statements.
    Excludes comments, blank lines, and docstrings.
    """
    executable = set()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.stmt) and hasattr(node, "lineno"):
                executable.add(node.lineno)
    except Exception as exc:
        pass
    return executable


def run_tests_with_tracer(py_files: Dict[str, Path]) -> Dict[str, Set[int]]:
    """Runs test suite under sys.settrace to capture executed lines per file."""
    import pytest

    executed_lines: Dict[str, Set[int]] = {norm_path: set() for norm_path in py_files}
    filename_cache: Dict[str, Any] = {}

    def tracer(frame, event, arg):
        if event == "line":
            f_name = frame.f_code.co_filename
            norm_name = filename_cache.get(f_name)
            if norm_name is False:
                return tracer
            if norm_name is None:
                # Fast substring check before path resolution
                if any(d in f_name for d in ["nlp", "services", "repositories", "utils", "models"]):
                    resolved = str(Path(f_name).resolve()).lower()
                    if resolved in executed_lines:
                        norm_name = resolved
                        filename_cache[f_name] = resolved
                    else:
                        filename_cache[f_name] = False
                        return tracer
                else:
                    filename_cache[f_name] = False
                    return tracer

            executed_lines[norm_name].add(frame.f_lineno)
        return tracer

    sys.settrace(tracer)
    pytest_start = time.perf_counter()
    ret_code = pytest.main(["-q"])
    pytest_duration = time.perf_counter() - pytest_start
    sys.settrace(None)

    print(f"\n[Test suite finished in {pytest_duration:.2f}s with exit code {ret_code}]")
    return executed_lines


def format_missing_ranges(missing: Set[int]) -> str:
    """Formats missing line numbers into compact ranges (e.g. '12-15, 23, 45-50')."""
    if not missing:
        return ""
    sorted_lines = sorted(missing)
    ranges = []
    start = sorted_lines[0]
    end = start

    for l in sorted_lines[1:]:
        if l == end + 1:
            end = l
        else:
            ranges.append(f"{start}-{end}" if start != end else str(start))
            start = end = l
    ranges.append(f"{start}-{end}" if start != end else str(start))
    res = ", ".join(ranges)
    return res if len(res) <= 30 else res[:27] + "..."


def generate_coverage_report():
    """Calculates coverage, prints table, and writes summary files."""
    print("=" * 80)
    print(" MEASURING NON-GUI CORE ERP STATEMENT COVERAGE")
    print("=" * 80)
    print(f" Target Packages: {', '.join(TARGET_DIRS)}")

    py_files = find_target_python_files()
    file_executable_lines: Dict[str, Set[int]] = {}
    for norm_path, p in py_files.items():
        file_executable_lines[norm_path] = extract_executable_statement_lines(p)

    executed_lines = run_tests_with_tracer(py_files)

    # Calculate statistics per file and per module
    module_stats: Dict[str, Dict[str, int]] = {d: {"exec": 0, "covered": 0} for d in TARGET_DIRS}
    file_rows: List[Dict[str, Any]] = []

    total_statements = 0
    total_covered = 0

    for norm_path, p in sorted(py_files.items(), key=lambda x: str(x[1])):
        rel_path = p.relative_to(PROJECT_ROOT).as_posix()
        top_dir = rel_path.split("/")[0]

        exec_set = file_executable_lines[norm_path]
        exec_count = len(exec_set)
        if exec_count == 0:
            continue

        exec_lines_set = executed_lines.get(norm_path, set())
        covered_set = exec_set.intersection(exec_lines_set)
        covered_count = len(covered_set)
        missed_set = exec_set - covered_set
        missed_count = len(missed_set)

        pct = (covered_count / exec_count * 100.0) if exec_count > 0 else 100.0

        if top_dir in module_stats:
            module_stats[top_dir]["exec"] += exec_count
            module_stats[top_dir]["covered"] += covered_count

        total_statements += exec_count
        total_covered += covered_count

        file_rows.append({
            "rel_path": rel_path,
            "module": top_dir,
            "statements": exec_count,
            "missed": missed_count,
            "covered": covered_count,
            "coverage_pct": round(pct, 1),
            "missing_ranges": format_missing_ranges(missed_set),
        })

    overall_pct = (total_covered / total_statements * 100.0) if total_statements > 0 else 0.0

    print("\n" + "=" * 80)
    print(f"{'Module / File':<42} | {'Stmts':<6} | {'Miss':<6} | {'Cover':<8} | {'Missing'}")
    print("-" * 80)

    curr_mod = ""
    for r in file_rows:
        if r["module"] != curr_mod:
            curr_mod = r["module"]
            mod_exec = module_stats[curr_mod]["exec"]
            mod_cov = module_stats[curr_mod]["covered"]
            mod_pct = (mod_cov / mod_exec * 100.0) if mod_exec > 0 else 0.0
            print(f"[{curr_mod.upper()}] - Package Coverage: {mod_pct:.1f}% ({mod_cov}/{mod_exec})")

        print(f"  {r['rel_path']:<40} | {r['statements']:<6} | {r['missed']:<6} | {r['coverage_pct']:>5.1f}% | {r['missing_ranges']}")

    print("=" * 80)
    print(f"{'TOTAL NON-GUI STATEMENTS':<42} | {total_statements:<6} | {total_statements - total_covered:<6} | {overall_pct:>5.1f}% |")
    print("=" * 80)

    # Export JSON
    summary_data = {
        "overall_coverage_pct": round(overall_pct, 2),
        "total_statements": total_statements,
        "total_covered": total_covered,
        "total_missed": total_statements - total_covered,
        "packages": {
            d: {
                "statements": module_stats[d]["exec"],
                "covered": module_stats[d]["covered"],
                "coverage_pct": round(
                    (module_stats[d]["covered"] / module_stats[d]["exec"] * 100.0)
                    if module_stats[d]["exec"] > 0
                    else 0.0,
                    2,
                ),
            }
            for d in TARGET_DIRS
        },
        "files": file_rows,
    }

    json_path = PROJECT_ROOT / "docs" / "coverage_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    # Export Markdown
    md_path = PROJECT_ROOT / "docs" / "COVERAGE.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Non-GUI Core Statement Coverage Report\n\n")
        f.write(f"- **Overall Core Coverage:** **{overall_pct:.2f}%**\n")
        f.write(f"- **Total Executable Statements:** **{total_statements}**\n")
        f.write(f"- **Total Statements Covered:** **{total_covered}**\n")
        f.write(f"- **Total Statements Missed:** **{total_statements - total_covered}**\n\n")
        f.write("## Package Level Summary\n\n")
        f.write("| Package | Statements | Covered | Coverage % |\n")
        f.write("| :--- | :---: | :---: | :---: |\n")
        for d in TARGET_DIRS:
            st = module_stats[d]
            pct_val = (st["covered"] / st["exec"] * 100.0) if st["exec"] > 0 else 0.0
            f.write(f"| `{d}/` | {st['exec']} | {st['covered']} | **{pct_val:.1f}%** |\n")
        f.write("\n## File Level Breakdown\n\n")
        f.write("| File | Statements | Missed | Coverage % | Missing Lines |\n")
        f.write("| :--- | :---: | :---: | :---: | :--- |\n")
        for r in file_rows:
            f.write(f"| `{r['rel_path']}` | {r['statements']} | {r['missed']} | {r['coverage_pct']:.1f}% | `{r['missing_ranges']}` |\n")

    print(f"\n[OK] Coverage report written to:")
    print(f"     - {json_path}")
    print(f"     - {md_path}\n")
    return summary_data


if __name__ == "__main__":
    generate_coverage_report()
