# LKW Structural Testing Workshop — Step-by-Step Guide
**Applying Laski-Korel-Weyuker Criteria to AI-Generated ADS Code**

---

## Project Structure

```
lkw-workshop/
├── java/
│   ├── src/
│   │   ├── AdaptiveCruiseController.java   ← Phase 1 (AI-generated module)
│   │   └── SensorParser.java               ← Phase 4 (Component Q)
│   └── test/
│       └── ADSTestSuite.java               ← All JUnit 5 tests (Phases 2–4)
├── python/
│   ├── du_analyzer.py                      ← Phase 2 static analysis tool
│   ├── lkw_analyzer.py                     ← Phases 2–3 extended tool
│   └── agent_generated_code.py             ← Python version of ACC logic
└── README.md                               ← This file
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Java | 17+     | `sudo apt install openjdk-17-jdk` |
| JUnit 5 JAR | 1.9+ | Download below |
| Python | 3.9+    | Already available on most systems |
| Git | any | `sudo apt install git` |

### Download JUnit 5 Standalone Runner
```bash
curl -L -o junit-platform-console-standalone.jar \
  https://repo1.maven.org/maven2/org/junit/platform/junit-platform-console-standalone/1.10.1/junit-platform-console-standalone-1.10.1.jar
```
Place the JAR in the `java/` directory.

---

## Part 0 — GitHub Setup

```bash
# 1. Initialise the repo
cd lkw-workshop
git init
git add .
git commit -m "Initial commit: LKW workshop skeleton"

# 2. Create a remote on GitHub (do this in the GitHub UI first, then:)
git remote add origin https://github.com/<your-username>/lkw-workshop.git
git branch -M main
git push -u origin main

# 3. Recommended branch workflow — one branch per phase:
git checkout -b phase/1-generation
git checkout -b phase/2-all-defs
git checkout -b phase/3-all-uses
git checkout -b phase/4-antidecomposition
```

### Recommended `.gitignore`
```
*.class
__pycache__/
*.pyc
*.jar
.idea/
```

---

## Phase 1 — The Agentic Generation (Black Box Problem)

### Objective
Understand what an AI agent produces and where structural proof is absent.

### Steps

**1. Read the generated code**
Open `java/src/AdaptiveCruiseController.java`. Read all the comments.
The key method is `calculateVelocity(radarDist, v2xSpeedLimit, isObstacleDetected)`.

**2. Identify the two deliberate faults (before running any tools)**
Try to spot them by reading the code:
- `safetyMargin` — is its initial value ever used?
- `collisionRisk` — does it affect *both* places it should?

These are the targets for Phases 2 and 3.

**3. Commit your reading notes**
```bash
git checkout phase/1-generation
# add any notes to a notes.txt file
git add notes.txt
git commit -m "Phase 1: read AI-generated code, identified candidate faults"
```

---

## Phase 2 — All-Definitions Audit (Dead Data)

### Objective
Prove that `safetyMargin = 0.5` (Def 1) is a Terminating Definition —
it is killed by Def 2 or Def 3 before any use, violating All-Defs.

### Steps

**1. Run the DU Analyzer on the Python version**
```bash
cd python
python du_analyzer.py agent_generated_code.py
```

Expected output:
```
⚠  Anomaly: 'safety_margin' redefined at line 34 before confirmed use
   (previously defined at line 31).
```

**2. Run the extended LKW Analyzer**
```bash
python lkw_analyzer.py agent_generated_code.py
```

Look at the `Terminating Definitions` section. You should see
`safety_margin` flagged twice (killed by Def 2, then Def 3).

**3. Map the DU pairs manually**
Draw this table in your notes:

| Variable | Definition | Def Line | Use | Use Line | Def-Clear? |
|----------|-----------|----------|-----|----------|------------|
| safetyMargin | `= 0.5` | 31 | none | — | ✗ VIOLATED |
| safetyMargin | `= 1.0` | 34 | `v2x_limit - safety_margin` | 38 | ✓ |
| safetyMargin | `= 0.0` | 36 | `v2x_limit - safety_margin` | 38 | ✓ |
| v2xSpeedLimit | parameter | entry | `v2x_limit > 100` (p-use) | 33 | ✓ |
| v2xSpeedLimit | parameter | entry | `v2x_limit - safety_margin` (c-use) | 38 | ✓ |

**4. Run the All-Defs JUnit tests**
```bash
cd ../java
javac -cp junit-platform-console-standalone.jar src/*.java test/*.java
java -cp .:src:test:junit-platform-console-standalone.jar \
     org.junit.platform.console.ConsoleLauncher \
     --select-class=ADSTestSuite \
     --include-classname=ADSTestSuite$AllDefsTest
```

Tests D-01 and D-02 pass (the code works for both branches).
Test D-03 passes as well — it documents that Def 1 is invisible to
execution, which is exactly the point: functional tests cannot detect
dead definitions.

**5. Fix the fault**
In `AdaptiveCruiseController.java`, replace lines 59–65 with:
```java
double safetyMargin = (v2xSpeedLimit > 100) ? 1.0 : 0.0;
double adjustedLimit = v2xSpeedLimit - safetyMargin;
```
This eliminates the dead Def 1 and makes the ternary the sole definition.

```bash
git checkout phase/2-all-defs
git add java/src/AdaptiveCruiseController.java
git commit -m "Phase 2: fix All-Defs violation — remove dead safetyMargin Def 1"
```

---

## Phase 3 — All-Uses Audit (Logic Leak)

### Objective
Prove that `collisionRisk` has a use (braking override) that the AI agent
forgot to implement — a "Logic Leak" where the system knows about a hazard
but does not act on it.

### Steps

**1. Inspect p-uses and c-uses in the LKW report**
Re-run:
```bash
cd python
python lkw_analyzer.py agent_generated_code.py
```

Look at the `P-Use Integrity warning` section.
`collision_risk` appears only in `c_uses` (line 53, inside the ternary),
NOT in `p_uses`. This means it controls no branching decision — the
braking override is missing.

**2. Trace the All-Uses requirement manually**
For `collisionRisk`, list every use:
- **Use 1** — `uiWarning = "COLLISION RISK" if collision_risk else ""`
  → This is a c-use (it's the condition of a ternary). ✓ EXISTS
- **Use 2** — `if collision_risk: target = 0.0`
  → This p-use (safety-critical branching decision) is ABSENT. ✗ MISSING

**3. Run the Logic Leak JUnit test (expect failure)**
```bash
cd ../java
java -cp .:src:test:junit-platform-console-standalone.jar \
     org.junit.platform.console.ConsoleLauncher \
     --select-class=ADSTestSuite \
     --include-classname=ADSTestSuite$AllUsesTest
```

Test **U-02** will FAIL:
```
expected: <0.0> but was: <5.0>
LOGIC LEAK: collisionRisk is set but does not override velocity
```
This is the correct outcome — the test has *found* the fault.

Tests U-01, U-03, U-04 will pass.

**4. Fix the fault**
In `AdaptiveCruiseController.java`, uncomment the override:
```java
// Find this block and uncomment the fix:
if (collisionRisk) {
    targetVelocity = 0.0;   // Use 2 — braking override
}
```

Re-run U-02 — it should now pass.

```bash
git checkout phase/3-all-uses
git add java/src/AdaptiveCruiseController.java
git commit -m "Phase 3: fix Logic Leak — wire collisionRisk into braking path (Use 2)"
```

---

## Phase 4 — Antidecomposition (Weyuker's 7th Axiom)

### Objective
Prove that system-level tests (Program P) can pass while component-level
faults (Component Q) remain hidden — then expose those faults with
dedicated unit tests.

### Steps

**1. Run ONLY the system-level tests (Program P)**
```bash
cd java
java -cp .:src:test:junit-platform-console-standalone.jar \
     org.junit.platform.console.ConsoleLauncher \
     --select-class=ADSTestSuite \
     --include-classname=ADSTestSuite$SystemTest
```

All three P tests (P-01, P-02, P-03) pass. No fault is visible.

**2. Run ONLY the component-level tests (Component Q)**
```bash
java -cp .:src:test:junit-platform-console-standalone.jar \
     org.junit.platform.console.ConsoleLauncher \
     --select-class=ADSTestSuite \
     --include-classname=ADSTestSuite$ComponentTest
```

Tests Q-02, Q-03, Q-04, Q-06 will FAIL:
- Q-02: negative distance accepted (non-physical value stored in lastValue)
- Q-03: `NullPointerException` thrown on null input
- Q-04: `NumberFormatException` thrown on malformed input
- Q-06: `lastValue` corrupted after failed parse

**3. Fill in the Comparative Fault Analysis table**
From the workshop PDF, Section 10:

| Fault Category     | LKW Criterion    | Detected by P? | Detected by Q? |
|--------------------|-----------------|----------------|----------------|
| Redundant Code     | All-Definitions  | No             | Yes            |
| Logic Leakage      | All-Uses         | No             | Yes            |
| State Drift        | All-DU-Paths     | No             | Yes            |
| Physical Bound Error | Antidecomposition | Partial      | Yes            |

**4. Fix SensorParser.java**
```java
public double parse(String raw) {
    if (raw == null) return 0.0;
    try {
        double value = Double.parseDouble(raw);
        if (value < 0) return 0.0;    // physical bound check
        lastValue = value;
        return value;
    } catch (NumberFormatException e) {
        return 0.0;    // sentinel on malformed input
    }
}
```

Re-run Component Q tests — all should pass.

**5. Run the full test suite**
```bash
java -cp .:src:test:junit-platform-console-standalone.jar \
     org.junit.platform.console.ConsoleLauncher \
     --select-class=ADSTestSuite
```

**6. Commit**
```bash
git checkout phase/4-antidecomposition
git add java/src/SensorParser.java
git commit -m "Phase 4: fix SensorParser — null guard, negative clamp, parse error handling"
```

---

## Final Deliverable Checklist

- [ ] Phase 1: `AdaptiveCruiseController.java` read and annotated
- [ ] Phase 2: DU-pair table completed; `du_analyzer.py` output captured
- [ ] Phase 2: All-Defs fault fixed and committed
- [ ] Phase 3: p-use / c-use table for `collisionRisk` completed
- [ ] Phase 3: Logic Leak test U-02 confirmed failing, then fixed
- [ ] Phase 4: System vs component test comparison table filled
- [ ] Phase 4: `SensorParser.java` fixed; Q-02 through Q-06 passing
- [ ] All commits on correct branches and pushed to GitHub

---

## Quick Reference: All Test IDs and Expected Results (after all fixes)

| Test | Phase | Description | Expected |
|------|-------|-------------|----------|
| P-01 | 4 | Normal cruising | PASS |
| P-02 | 4 | Obstacle stop | PASS |
| P-03 | 4 | V2X clamp | PASS |
| Q-01 | 4 | Valid parse | PASS |
| Q-02 | 4 | Negative distance | FAIL → PASS after fix |
| Q-03 | 4 | Null input | FAIL → PASS after fix |
| Q-04 | 4 | Malformed string | FAIL → PASS after fix |
| Q-05 | 4 | Extreme value | PASS |
| Q-06 | 4 | lastValue after error | FAIL → PASS after fix |
| D-01 | 2 | High V2X branch | PASS |
| D-02 | 2 | Low V2X branch | PASS |
| D-03 | 2 | Dead Def documentation | PASS (structural) |
| U-01 | 3 | UI warning set | PASS |
| U-02 | 3 | Logic Leak braking | FAIL → PASS after fix |
| U-03 | 3 | No collision, normal | PASS |
| U-04 | 3 | Both flags active | PASS |
