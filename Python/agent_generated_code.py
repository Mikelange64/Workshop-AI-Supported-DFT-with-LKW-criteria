"""
agent_generated_code.py
───────────────────────
This is the Python equivalent of AdaptiveCruiseController.java.

It exists so the DUAnalyzer and LKWAnalyzer Python tools (which operate on
Python ASTs) can analyse the same logic as the Java implementation.

Run against the static analysis tools:
    python du_analyzer.py  agent_generated_code.py
    python lkw_analyzer.py agent_generated_code.py
"""


def calculate_velocity(radar_dist: float,
                        v2x_limit: float,
                        is_obstacle: bool) -> float:
    """
    Faults deliberately preserved for LKW analysis:

    FAULT 1 — All-Defs (Terminating Definition):
        safety_margin = 0.5   ← Def 1, killed by Def 2 or Def 3.
        No definition-clear path exists from Def 1 to any use.

    FAULT 2 — All-Uses (Logic Leak):
        collision_risk controls uiWarning (Use 1) but is NOT used to
        override `target` velocity (Use 2 is absent).
    """

    # ── FAULT 1: Terminating Definition ─────────────────────────────────────
    safety_margin = 0.5   # Def 1  — NEVER reaches the return path

    if v2x_limit > 100:
        safety_margin = 1.0   # Def 2
    else:
        safety_margin = 0.0   # Def 3

    adjusted_limit = v2x_limit - safety_margin   # only Def 2 or Def 3 reaches here

    # ── Core velocity logic ──────────────────────────────────────────────────
    if is_obstacle:
        target = 0.0
    else:
        target = min(radar_dist, adjusted_limit)

    # ── FAULT 2: Logic Leak ──────────────────────────────────────────────────
    collision_risk = False

    if radar_dist < 10.0:         # p-use of radar_dist
        collision_risk = True

    # Use 1: collision_risk → UI warning  (EXISTS ✓)
    ui_warning = "COLLISION RISK" if collision_risk else ""   # p-use of collision_risk

    # Use 2: collision_risk → velocity override  (MISSING ✗)
    # if collision_risk:
    #     target = 0.0

    return target
