import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

/**
 * ADSTestSuite.java
 * ─────────────────
 * LKW structural test suite — matches the clean AI-generated source files.
 *
 * Nested classes mirror the workshop phases:
 *
 *   SystemTest       — Phase 4, Program P (integration tests)
 *   ComponentTest    — Phase 4, Component Q (unit tests, Antidecomposition)
 *   AllDefsTest      — Phase 2, All-Definitions audit
 *   AllUsesTest      — Phase 3, All-Uses audit
 */
class ADSTestSuite {

    // ════════════════════════════════════════════════════════════════════════
    // Phase 4a — Program P: System-Level Integration
    // ════════════════════════════════════════════════════════════════════════
    @Nested
    @DisplayName("Program P: System-Level Integration")
    class SystemTest {

        @Test
        @DisplayName("P-01 | No obstacle, speed below V2X limit → returns radarDist")
        void testNormalCruising() {
            AdaptiveCruiseController acc = new AdaptiveCruiseController();
            double result = acc.calculateVelocity(50.0, 60.0, false);
            assertEquals(50.0, result, 0.01);
        }

        @Test
        @DisplayName("P-02 | Obstacle detected → velocity = 0")
        void testObstacleStop() {
            AdaptiveCruiseController acc = new AdaptiveCruiseController();
            double result = acc.calculateVelocity(30.0, 60.0, true);
            assertEquals(0.0, result);
        }

        @Test
        @DisplayName("P-03 | V2X limit lower than radarDist → clamps to V2X limit")
        void testV2XClamp() {
            AdaptiveCruiseController acc = new AdaptiveCruiseController();
            double result = acc.calculateVelocity(80.0, 40.0, false);
            assertEquals(40.0, result, 0.01);
        }

        @Test
        @DisplayName("P-04 | radarDist and V2X limit equal → returns that value")
        void testEqualSpeedAndLimit() {
            AdaptiveCruiseController acc = new AdaptiveCruiseController();
            double result = acc.calculateVelocity(60.0, 60.0, false);
            assertEquals(60.0, result, 0.01);
        }
    }

    // ════════════════════════════════════════════════════════════════════════
    // Phase 4b — Component Q: Isolated Data Integrity (Antidecomposition)
    // ════════════════════════════════════════════════════════════════════════
    @Nested
    @DisplayName("Component Q: Isolated Data Integrity (Antidecomposition)")
    class ComponentTest {

        @Test
        @DisplayName("Q-01 | Valid positive string → parsed correctly")
        void testNormalParse() {
            SensorParser parser = new SensorParser();
            double result = parser.parse("42.7");
            assertEquals(42.7, result, 0.001);
        }

        @Test
        @DisplayName("Q-02 | getLastValue() reflects most recent parse")
        void testLastValueUpdated() {
            SensorParser parser = new SensorParser();
            parser.parse("30.0");
            assertEquals(30.0, parser.getLastValue(), 0.001);
        }

        @Test
        @DisplayName("Q-03 | Negative value → accepted or rejected? (boundary check)")
        void testNegativeDistance() {
            SensorParser parser = new SensorParser();
            double result = parser.parse("-1.0");
            // Document what the agent produced — no assertion on correctness,
            // just verify it does not throw and record the result.
            assertTrue(result == -1.0,
                "Agent accepts negative distance — physical bound not enforced");
        }

        @Test
        @DisplayName("Q-04 | Null input → throws NullPointerException (no null guard)")
        void testNullInput() {
            SensorParser parser = new SensorParser();
            assertThrows(NullPointerException.class,
                () -> parser.parse(null),
                "Agent-generated code throws NPE on null — no null guard present");
        }

        @Test
        @DisplayName("Q-05 | Malformed string → throws NumberFormatException (no error handling)")
        void testMalformedString() {
            SensorParser parser = new SensorParser();
            assertThrows(NumberFormatException.class,
                () -> parser.parse("SENSOR_ERR"),
                "Agent-generated code throws on malformed input — no try/catch present");
        }

        @Test
        @DisplayName("Q-06 | Extreme value (MAX_DOUBLE) → parsed without overflow")
        void testExtremeValue() {
            SensorParser parser = new SensorParser();
            assertDoesNotThrow(
                () -> parser.parse(String.valueOf(Double.MAX_VALUE))
            );
        }
    }

    // ════════════════════════════════════════════════════════════════════════
    // Phase 2 — All-Definitions Audit
    // ════════════════════════════════════════════════════════════════════════
    @Nested
    @DisplayName("Phase 2 — All-Definitions (DU-Pair Audit)")
    class AllDefsTest {

        @Test
        @DisplayName("D-01 | v2xSpeedLimit defined as parameter → reaches p-use in condition")
        void testV2XSpeedLimitReachesPUse() {
            AdaptiveCruiseController acc = new AdaptiveCruiseController();
            // v2xSpeedLimit is used in Math.min() — c-use
            double result = acc.calculateVelocity(80.0, 40.0, false);
            assertEquals(40.0, result, 0.01,
                "v2xSpeedLimit must reach the Math.min() computation (c-use)");
        }

        @Test
        @DisplayName("D-02 | radarDist defined as parameter → reaches c-use in Math.min()")
        void testRadarDistReachesCUse() {
            AdaptiveCruiseController acc = new AdaptiveCruiseController();
            double result = acc.calculateVelocity(50.0, 60.0, false);
            assertEquals(50.0, result, 0.01,
                "radarDist must reach the Math.min() computation (c-use)");
        }

        @Test
        @DisplayName("D-03 | isObstacleDetected defined as parameter → reaches p-use in if-condition")
        void testIsObstacleDetectedReachesPUse() {
            AdaptiveCruiseController acc = new AdaptiveCruiseController();
            // True branch
            assertEquals(0.0, acc.calculateVelocity(50.0, 60.0, true));
            // False branch
            assertEquals(50.0, acc.calculateVelocity(50.0, 60.0, false), 0.01);
        }

        @Test
        @DisplayName("D-04 | targetVelocity definition in obstacle branch → reaches return")
        void testTargetVelocityObstacleBranch() {
            AdaptiveCruiseController acc = new AdaptiveCruiseController();
            double result = acc.calculateVelocity(50.0, 60.0, true);
            assertEquals(0.0, result,
                "targetVelocity=0.0 definition must reach the return statement");
        }

        @Test
        @DisplayName("D-05 | targetVelocity definition in else branch → reaches return")
        void testTargetVelocityElseBranch() {
            AdaptiveCruiseController acc = new AdaptiveCruiseController();
            double result = acc.calculateVelocity(50.0, 60.0, false);
            assertEquals(50.0, result, 0.01,
                "targetVelocity=Math.min() definition must reach the return statement");
        }
    }

    // ════════════════════════════════════════════════════════════════════════
    // Phase 3 — All-Uses Audit
    // ════════════════════════════════════════════════════════════════════════
    @Nested
    @DisplayName("Phase 3 — All-Uses Audit")
    class AllUsesTest {

        @Test
        @DisplayName("U-01 | isObstacleDetected=true → velocity=0 (p-use, true branch)")
        void testObstacleDetectedTrueBranch() {
            AdaptiveCruiseController acc = new AdaptiveCruiseController();
            assertEquals(0.0, acc.calculateVelocity(50.0, 60.0, true));
        }

        @Test
        @DisplayName("U-02 | isObstacleDetected=false → Math.min() branch taken (p-use, false branch)")
        void testObstacleDetectedFalseBranch() {
            AdaptiveCruiseController acc = new AdaptiveCruiseController();
            assertEquals(50.0, acc.calculateVelocity(50.0, 60.0, false), 0.01);
        }

        @Test
        @DisplayName("U-03 | v2xSpeedLimit is lower → c-use in Math.min() selects it")
        void testV2XLimitSelectedByMin() {
            AdaptiveCruiseController acc = new AdaptiveCruiseController();
            assertEquals(40.0, acc.calculateVelocity(80.0, 40.0, false), 0.01);
        }

        @Test
        @DisplayName("U-04 | radarDist is lower → c-use in Math.min() selects it")
        void testRadarDistSelectedByMin() {
            AdaptiveCruiseController acc = new AdaptiveCruiseController();
            assertEquals(30.0, acc.calculateVelocity(30.0, 60.0, false), 0.01);
        }

        @Test
        @DisplayName("U-05 | currentVelocity updated after each call (c-use via getter)")
        void testCurrentVelocityUpdated() {
            AdaptiveCruiseController acc = new AdaptiveCruiseController();
            acc.calculateVelocity(50.0, 60.0, false);
            assertEquals(50.0, acc.getCurrentVelocity(), 0.01);
        }
    }
}