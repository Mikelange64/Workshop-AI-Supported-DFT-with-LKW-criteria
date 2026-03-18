"""
lkw_analyzer.py
───────────────
Phases 2 & 3 — Extended Static Analysis Tool
Workshop section 8, Listing 2

Extends DUAnalyzer to categorise every variable use as either:

  p-use  — Predicate use: the variable appears in the test expression of
            an `if` or `while` statement (controls a branching decision).

  c-use  — Computational use: the variable is read in any other context
            (arithmetic, assignment RHS, return, function call, etc.).

Also tracks Terminating Definitions (same as DUAnalyzer).

Usage:
    python lkw_analyzer.py agent_generated_code.py
    python lkw_analyzer.py --demo
"""

import ast
import sys
from collections import defaultdict


# ── Core Visitor ─────────────────────────────────────────────────────────────

class LKWAnalyzer(ast.NodeVisitor):
    """
    Traverses an AST and classifies every variable use.

    Attributes
    ----------
    definitions  : dict  – active pending definitions  {var: line}
    p_uses       : list  – (var, line) tuples for predicate uses
    c_uses       : list  – (var, line) tuples for computational uses
    terminations : list  – (var, line) tuples where a definition was killed
    """

    def __init__(self):
        self.definitions:  dict[str, int]       = {}
        self.p_uses:       list[tuple[str, int]] = []
        self.c_uses:       list[tuple[str, int]] = []
        self.terminations: list[tuple[str, int]] = []

        # Internal: set of (var, line) pairs already recorded as p-uses,
        # so visit_Name does not double-count them as c-uses.
        self._p_use_set: set[tuple[str, int]] = set()

    # ── Assignment tracking ──────────────────────────────────────────────────

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                if var_name in self.definitions:
                    self.terminations.append((var_name, node.lineno))
                self.definitions[var_name] = node.lineno
        self.generic_visit(node)

    # ── Predicate-use detection (if / while tests) ───────────────────────────

    def _record_p_uses_in_expression(self, expr_node: ast.expr, line: int) -> None:
        """Walk a test expression and record every Name load as a p-use."""
        for name_node in ast.walk(expr_node):
            if isinstance(name_node, ast.Name) and isinstance(name_node.ctx, ast.Load):
                record = (name_node.id, line)
                self.p_uses.append(record)
                self._p_use_set.add(record)

    def visit_If(self, node: ast.If) -> None:
        self._record_p_uses_in_expression(node.test, node.lineno)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._record_p_uses_in_expression(node.test, node.lineno)
        self.generic_visit(node)

    # ── Computational-use detection (everything else) ────────────────────────

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            record = (node.id, node.lineno)
            # Only record as c-use if not already captured as a p-use
            if record not in self._p_use_set:
                self.c_uses.append(record)
        self.generic_visit(node)


# ── Report helpers ────────────────────────────────────────────────────────────

def _group_by_var(pairs: list[tuple[str, int]]) -> dict[str, list[int]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for var, line in pairs:
        grouped[var].append(line)
    return dict(grouped)


def print_report(analyzer: LKWAnalyzer, label: str = "<source>") -> None:
    print(f"\n{'═' * 64}")
    print(f"  LKW Analyzer — {label}")
    print(f"{'═' * 64}")

    # ── Terminating Definitions ──────────────────────────────────────────────
    print("\n── Terminating Definitions (All-Defs violations) ─────────────")
    if analyzer.terminations:
        for var, line in analyzer.terminations:
            print(f"  ⚠  '{var}' re-assigned at line {line} before prior def was used")
    else:
        print("  ✓  None detected")

    # ── P-Uses ───────────────────────────────────────────────────────────────
    print("\n── Predicate Uses (p-uses) ───────────────────────────────────")
    p_grouped = _group_by_var(analyzer.p_uses)
    if p_grouped:
        for var, lines in sorted(p_grouped.items()):
            print(f"  {var:30s}  lines: {lines}")
    else:
        print("  (none)")

    # ── C-Uses ───────────────────────────────────────────────────────────────
    print("\n── Computational Uses (c-uses) ───────────────────────────────")
    c_grouped = _group_by_var(analyzer.c_uses)
    if c_grouped:
        for var, lines in sorted(c_grouped.items()):
            print(f"  {var:30s}  lines: {lines}")
    else:
        print("  (none)")

    # ── Structural Adequacy Assessment ──────────────────────────────────────
    print("\n── Structural Adequacy Assessment ────────────────────────────")

    # Check 1: safety-critical variables that appear only in c-uses (no p-use)
    c_only = set(c_grouped.keys()) - set(p_grouped.keys())
    if c_only:
        print(f"\n  P-Use Integrity warning — these variables are used computationally")
        print(f"  but NEVER in a predicate (boundary checks may be missing):")
        for v in sorted(c_only):
            print(f"    → '{v}'")
    else:
        print("\n  ✓  All variables with c-uses also appear in at least one p-use")

    # Check 2: p-use count vs c-use count (rough test-case sufficiency hint)
    total_p = len(analyzer.p_uses)
    if total_p > 0:
        print(f"\n  Path Exhaustion hint: {total_p} predicate use(s) detected.")
        print(f"  Each p-use requires TRUE + FALSE test cases → "
              f"minimum {total_p * 2} test cases for All-Uses coverage.")

    print()


# ── Demo code ─────────────────────────────────────────────────────────────────

DEMO_CODE = '''
def calculate_velocity(radar_dist, v2x_limit, is_obstacle):
    safety_margin = 0.5       # Def 1 — killed by Def 2 or 3

    if v2x_limit > 100:
        safety_margin = 1.0   # Def 2
    else:
        safety_margin = 0.0   # Def 3

    adjusted = v2x_limit - safety_margin

    if is_obstacle:
        target = 0.0
    else:
        target = min(radar_dist, adjusted)

    collision_risk = False
    if radar_dist < 10.0:
        collision_risk = True

    # Use 1 of collision_risk — UI only
    warning = "ALERT" if collision_risk else ""

    # Use 2 of collision_risk is MISSING here (Logic Leak):
    # if collision_risk:
    #     target = 0.0

    return target
'''


# ── Entry point ───────────────────────────────────────────────────────────────

def run(source_code: str, label: str) -> None:
    tree = ast.parse(source_code)
    analyzer = LKWAnalyzer()
    analyzer.visit(tree)
    print_report(analyzer, label)


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--demo":
        run(DEMO_CODE, "built-in demo (workshop Listing 2)")
    elif len(sys.argv) == 2:
        with open(sys.argv[1], "r") as f:
            source = f.read()
        run(source, sys.argv[1])
    else:
        run(DEMO_CODE, "built-in demo (workshop Listing 2)")
        print("Tip: python lkw_analyzer.py your_file.py\n")
