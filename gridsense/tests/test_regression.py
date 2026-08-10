"""
Regression + robustness suite.

Goes beyond the happy-path offline tests: malformed input, empty data, missing
columns, boundary conditions, and the invariants that must never regress
(human-in-the-loop, no-invented-data, guard suppression). Mocks only the network.
"""
import os
import sys
import io
import csv
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.schema import Reading, Anomaly, PlantContext
from app.detectors import detect, detect_fleet, performance_ratio, expected_power_kw
from app.agent import build_workitem, _approval_policy, _normalise_causes
from app.pipeline import read_telemetry, detect_all, _coerce


def _tmp_csv(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
    f.write(text); f.close()
    return f.name


# ---------- input robustness ----------
def test_empty_metrics_never_crash():
    r = Reading("X", "SolarInverter", "t", {})
    assert detect(r) == []        # no data -> no false alarm, no crash
    assert performance_ratio(r) is None
    assert expected_power_kw(r) is None
    print("  ✓ empty metrics: no crash, no false alarm")


def test_missing_columns_csv():
    # Only the 3 mandatory columns, no metric columns at all.
    path = _tmp_csv("asset_id,asset_type,timestamp\nINV-1,SolarInverter,t\n")
    readings = read_telemetry(path)
    assert len(readings) == 1 and readings[0].metrics == {}
    assert detect_all(readings) == []
    print("  ✓ CSV with no metric columns handled gracefully")


def test_malformed_values_coerce_safely():
    assert _coerce("") is None
    assert _coerce("abc") == "abc"       # non-numeric stays string, no crash
    assert _coerce("3.0") == 3
    assert _coerce("3.5") == 3.5
    assert _coerce("-1") == -1
    print("  ✓ malformed / mixed-type cells coerced without error")


def test_garbage_text_in_numeric_field():
    # A sensor emitting 'ERR' where a number is expected must not crash detection.
    path = _tmp_csv(
        "asset_id,asset_type,timestamp,power_kw,irradiance_wm2,rated_kw\n"
        "INV-1,SolarInverter,t,ERR,800,660\n")
    readings = read_telemetry(path)
    # power_kw is a string 'ERR'; detectors compare with .get(...,0) numeric guards
    try:
        anomalies = detect_all(readings)
        print(f"  ✓ garbage numeric value tolerated ({len(anomalies)} anomalies, no crash)")
    except Exception as e:
        raise AssertionError(f"detection crashed on garbage input: {e}")


def test_empty_file():
    path = _tmp_csv("asset_id,asset_type,timestamp,power_kw\n")
    assert read_telemetry(path) == []
    assert detect_all(read_telemetry(path)) == []
    print("  ✓ empty telemetry file -> empty result")


# ---------- detector boundary conditions ----------
def test_peer_needs_minimum_sample():
    # With <3 producing inverters, peer comparison must stay silent (no false laggard).
    readings = [Reading(f"INV-{i}", "SolarInverter", "t",
                        {"power_kw": kw, "rated_kw": 660})
                for i, kw in enumerate([540, 100], start=1)]
    assert detect_fleet(readings) == []
    print("  ✓ peer detector requires a minimum peer sample (no false positives)")


def test_peer_ignores_offline_units():
    # A fully-offline inverter (0 kW) must not drag the peer median down.
    readings = [Reading(f"INV-{i}", "SolarInverter", "t",
                        {"power_kw": kw, "rated_kw": 660})
                for i, kw in enumerate([540, 545, 538, 0], start=1)]
    fired = [a.asset_id for a in detect_fleet(readings)]
    # the 0 kW unit is handled by the no-output detector, not peer comparison
    assert "INV-4" not in fired
    print("  ✓ peer comparison excludes offline units from the median")


def test_pr_boundary():
    # Exactly at threshold should not fire; clearly below should.
    at = Reading("A", "SolarInverter", "t", {"power_kw": 528, "irradiance_wm2": 1000, "rated_kw": 660})
    below = Reading("B", "SolarInverter", "t", {"power_kw": 400, "irradiance_wm2": 1000, "rated_kw": 660})
    assert "inverter_low_pr" not in [a.rule for a in detect(at)]
    assert "inverter_low_pr" in [a.rule for a in detect(below)]
    print("  ✓ PR detector respects its threshold boundary")


# ---------- invariants that must never regress ----------
def test_invariant_actionable_always_needs_approval():
    for action in ("DispatchTechnician", "RemoteReset", "ScheduleMaintenance"):
        assert _approval_policy({"action": action, "confidence": 0.99}) is True
    print("  ✓ INVARIANT: asset-touching actions always require human approval")


def test_invariant_guards_suppress_when_grid_down():
    readings = read_telemetry(
        os.path.join(os.path.dirname(__file__), "..", "samples", "plant_telemetry.csv"))
    assert len(detect_all(readings)) > 0
    assert len(detect_all(readings, PlantContext(grid_available=False))) == 0
    print("  ✓ INVARIANT: grid-down suppresses all output-loss alarms")


def test_invariant_probabilities_normalise():
    # Even if the model returns unnormalised weights, they must sum to ~1.
    causes = _normalise_causes([{"cause": "a", "probability": 2.0},
                                {"cause": "b", "probability": 2.0}])
    assert abs(sum(c["probability"] for c in causes) - 1.0) < 0.02
    assert causes[0]["probability"] == 0.5
    print("  ✓ INVARIANT: probable-cause weights always normalise")


def test_invariant_no_invented_fields():
    class Fake:
        model = "fake"
        def triage(self, a):
            return {"severity": "Low", "action": "MonitorOnly", "confidence": 0.9,
                    "title": "t", "likely_cause": "c", "probable_causes": [],
                    "recommended_steps": [], "reasoning": "r"}
    a = Anomaly("X", "SolarInverter", "t", "rule", "d", {"power_kw": 5})
    w = build_workitem(a, Fake())
    # nothing the model didn't provide should appear
    assert w.est_energy_loss_kwh is None
    assert w.est_revenue_loss is None
    assert w.peer_median_kw is None
    print("  ✓ INVARIANT: unstated fields stay null (no hallucinated data)")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    print(f"\nRunning {len(tests)} regression / robustness tests…\n")
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {t.__name__}: {e}")
    if failed:
        print(f"\n{failed} FAILED / {len(tests)}"); sys.exit(1)
    print(f"\nAll {len(tests)} regression tests passed.\n")
