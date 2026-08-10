"""
Offline verification. Detectors are pure functions (fully testable). The agent
is mocked so we can verify work-item building and the approval policy without a
network call or API key.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.schema import Reading, Anomaly, PlantContext
from app.detectors import detect, detect_fleet, performance_ratio, expected_power_kw
from app.agent import build_workitem, _approval_policy, _normalise_causes
from app.pipeline import read_telemetry, scan_only, detect_all


def test_inverter_no_output_detected():
    r = Reading("INV-02", "SolarInverter", "t", {"power_kw": 0, "irradiance_wm2": 790, "temp_c": 62})
    fired = [a.rule for a in detect(r)]
    assert "inverter_no_output" in fired
    print("  ✓ tripped inverter detected")


def test_healthy_inverter_no_anomaly():
    r = Reading("INV-01", "SolarInverter", "t", {"power_kw": 540, "irradiance_wm2": 820, "temp_c": 58})
    assert detect(r) == []
    print("  ✓ healthy inverter produces no anomaly")


def test_turbine_vibration_and_gearbox():
    r = Reading("WTG-09", "WindTurbine", "t",
                {"power_kw": 2200, "wind_ms": 12, "rated_kw": 2500,
                 "gearbox_temp_c": 83, "vibration_mm_s": 3.4})
    fired = [a.rule for a in detect(r)]
    assert "gearbox_overtemp" in fired
    print("  ✓ gearbox overtemp detected")


def test_csv_ingest_and_scan():
    path = os.path.join(os.path.dirname(__file__), "..", "samples", "plant_telemetry.csv")
    readings = read_telemetry(path)
    assert len(readings) == 14
    anomalies = scan_only(path)
    # We seeded several faults; make sure the engine finds a healthy handful.
    rules = {a.rule for a in anomalies}
    for expected in ["inverter_no_output", "inverter_overtemp", "string_undervoltage",
                     "turbine_underperform", "gearbox_overtemp", "turbine_vibration",
                     "transformer_overtemp", "transformer_overload",
                     "tracker_misalign", "meter_comm_loss"]:
        assert expected in rules, f"missing detector: {expected}"
    print(f"  ✓ CSV ingest + all 10 fault types detected ({len(anomalies)} anomalies)")


class FakeAgent:
    model = "fake"
    def __init__(self, resp): self._r = resp
    def triage(self, a): return self._r


def test_build_workitem_and_approval():
    a = Anomaly("TRF-02", "Transformer", "t", "transformer_overload",
                "loaded 112%", {"load_pct": 112, "oil_temp_c": 94})
    fake = FakeAgent({
        "severity": "Critical", "action": "DispatchTechnician", "confidence": 0.95,
        "title": "Transformer overloaded and hot", "likely_cause": "Sustained overload",
        "recommended_steps": ["Reduce load", "Inspect cooling", "Check oil"],
        "est_energy_loss_kwh": None, "reasoning": "Overload + high oil temp is a safety risk.",
    })
    w = build_workitem(a, fake)
    assert w.severity == "Critical"
    assert w.needs_human_approval is True          # asset-touching action -> approval
    assert w.work_id.startswith("WO-")
    assert len(w.recommended_steps) == 3
    print("  ✓ work item built; asset action requires approval")


def test_monitor_only_can_skip_approval():
    assert _approval_policy({"action": "MonitorOnly", "confidence": 0.9}) is False
    assert _approval_policy({"action": "MonitorOnly", "confidence": 0.5}) is True
    assert _approval_policy({"action": "RemoteReset", "confidence": 0.99}) is True
    print("  ✓ approval policy conservative (only confident monitor/ticket skip)")


def test_performance_ratio():
    # 390 kW actual vs 660 rated * (815/1000) = 538 expected -> PR ~0.73
    r = Reading("INV-04", "SolarInverter", "t",
                {"power_kw": 390, "irradiance_wm2": 815, "rated_kw": 660})
    pr = performance_ratio(r)
    assert pr is not None and 0.70 < pr < 0.76
    assert round(expected_power_kw(r)) == 538
    print(f"  ✓ performance ratio computed correctly (PR={pr:.2f})")


def test_pr_detector_fires_on_underperformance():
    r = Reading("INV-04", "SolarInverter", "t",
                {"power_kw": 390, "irradiance_wm2": 815, "rated_kw": 660})
    assert "inverter_low_pr" in [a.rule for a in detect(r)]
    print("  ✓ low-PR detector catches partial underperformance")


def test_peer_comparison_catches_silent_loss():
    # Four healthy peers ~540, one silent laggard at 390 -> flagged.
    readings = [
        Reading(f"INV-0{i}", "SolarInverter", "t",
                {"power_kw": kw, "irradiance_wm2": 815, "rated_kw": 660})
        for i, kw in enumerate([540, 505, 548, 390, 545], start=1)
    ]
    fired = detect_fleet(readings)
    laggards = [a.asset_id for a in fired if a.rule == "inverter_peer_underperform"]
    assert "INV-04" in laggards
    # the healthy ones must NOT be flagged
    assert "INV-01" not in laggards and "INV-05" not in laggards
    print("  ✓ peer comparison flags the silent laggard, not its healthy siblings")


def test_guard_conditions_suppress_false_alarms():
    readings = read_telemetry(
        os.path.join(os.path.dirname(__file__), "..", "samples", "plant_telemetry.csv"))
    normal = detect_all(readings)
    assert len(normal) > 0
    # grid down -> output-loss alarms suppressed entirely
    assert len(detect_all(readings, PlantContext(grid_available=False))) == 0
    # asset under maintenance -> its alarms suppressed
    maint = detect_all(readings, PlantContext(assets_in_maintenance=("INV-02",)))
    assert "INV-02" not in [a.asset_id for a in maint]
    print("  ✓ guard conditions suppress alarms the plant state already explains")


def test_financial_impact_from_energy_loss():
    a = Anomaly("INV-02", "SolarInverter", "t", "inverter_no_output",
                "offline", {"power_kw": 0, "irradiance_wm2": 790, "rated_kw": 660})
    fake = FakeAgent({
        "severity": "High", "action": "RemoteReset", "confidence": 0.88,
        "title": "INV-02 offline", "likely_cause": "Protection trip",
        "probable_causes": [{"cause": "trip", "probability": 0.55},
                            {"cause": "comms loss", "probability": 0.25},
                            {"cause": "grid outage", "probability": 0.20}],
        "recommended_steps": ["Ping inverter", "Attempt remote reset"],
        "est_energy_loss_kwh": 520, "reasoning": "Large live loss.",
    })
    w = build_workitem(a, fake)
    assert w.est_revenue_loss == 520 * 5.2       # kWh x tariff
    assert w.currency == "INR"
    # probable causes normalised and sorted descending
    assert w.probable_causes[0]["cause"] == "trip"
    assert abs(sum(c["probability"] for c in w.probable_causes) - 1.0) < 0.01
    print(f"  ✓ financial impact ₹{w.est_revenue_loss:,.0f} + ranked causes computed")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    print(f"\nRunning {len(tests)} offline tests…\n")
    for t in tests:
        t()
    print(f"\nAll {len(tests)} tests passed. Detectors + pipeline verified without an API key.\n")
