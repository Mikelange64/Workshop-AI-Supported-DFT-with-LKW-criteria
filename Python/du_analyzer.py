"""
du_analyzer.py
──────────────
Phase 2 — All-Definitions Audit Tool
Workshop section 7, Listing 1

Detects "Terminating Definitions": variables that are redefined before
their first value is ever consumed.

Usage:
    python du_analyzer.py agent_generated_code.py
    python du_analyzer.py --demo          # runs the built-in example
"""

import ast
import sys


# ── Core Visitor ────────────────────────────────────────────────────────────

class DUAnalyzer(ast.NodeVisitor):
    """
    Walks an AST and records assignment (definition) vs load (use) events.

    A violation is flagged whenever a variable is re-assigned before its
    current definition has been consumed by any load expression.
    """

    def __init__(self):
        # Maps var_name → line_number_of_current_pending_definition
        self.definitions: dict[str, int] = {}
        self.violations:  list[str]      = []

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                if var_name in self.definitions:
                    # A prior definition exists and has never been used —
                    # this is the "Terminating Definition" anomaly.
                    self.violations.append(
                        f"Anomaly: '{var_name}' redefined at line {node.lineno} "
                        f"before confirmed use "
                        f"(previously defined at line {self.definitions[var_name]})."
                    )
                self.definitions[var_name] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        # A Load context = a "use" of the variable.
        # Clear the pending definition so we don't report it as killed.
        if isinstance(node.ctx, ast.Load) and node.id in self.definitions:
            del self.definitions[node.id]
        self.generic_visit(node)


# ── Demo / file audit ────────────────────────────────────────────────────────

DEMO_CODE = '''
def calculate_speed(radar_dist, v2x_limit):
    margin = 0.5          # Def 1  (killed by Def 2 or Def 3 — never used)
    if v2x_limit > 100:
        margin = 1.0      # Def 2
    else:
        margin = 0.0      # Def 3
    return radar_dist + margin
'''


def run_analysis(source_code: str, label: str = "<source>") -> None:
    print(f"\n{'═' * 60}")
    print(f"  DU Analyzer — {label}")
    print(f"{'═' * 60}")

    tree = ast.parse(source_code)
    analyzer = DUAnalyzer()
    analyzer.visit(tree)

    if analyzer.violations:
        print(f"\n⚠  {len(analyzer.violations)} All-Defs violation(s) found:\n")
        for v in analyzer.violations:
            print(f"  → {v}")
    else:
        print("\n✓  No All-Defs violations detected.")

    print()


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--demo":
        run_analysis(DEMO_CODE, label="built-in demo (workshop Listing 1)")
    elif len(sys.argv) == 2:
        file_path = sys.argv[1]
        with open(file_path, "r") as f:
            source = f.read()
        run_analysis(source, label=file_path)
    else:
        # Default: run the demo
        run_analysis(DEMO_CODE, label="built-in demo (workshop Listing 1)")
        print("Tip: pass a .py file path to audit real agent-generated code.")
        print("     python du_analyzer.py agent_generated_code.py\n")
