"""
Anomaly detection — the deterministic RPA layer.

Plain, explainable rules over telemetry. This is intentionally NOT the AI:
in a real plant you want the cheap, auditable rule engine to sift millions of
rows, and only escalate the interesting deviations to the (more expensive)
reasoning agent. Rules are easy to defend to an O&M engineer.

Two families of detector:
  • Per-reading detectors — look at one asset in isolation (threshold, PR).
  • Fleet detectors — compare an asset against its healthy siblings
    (peer comparison), which catches silent 5-15% underperformance that no
    fixed threshold can. Both were called out by industry review as core.
"""
from __future__ import annotations
from statistics import median

from .schema import Reading, Anomaly
from .config import PR_ALERT_THRESHOLD, PEER_UNDERPERF_RATIO, STC_IRRADIANCE


def _mk(r: Reading, rule: str, detail: str) -> Anomaly:
    return Anomaly(
        asset_id=r.asset_id, asset_type=r.asset_type, timestamp=r.timestamp,
        rule=rule, detail=detail, metrics=dict(r.metrics),
    )


class _NumSafe:
    """
    Wraps a metrics dict so numeric comparisons never crash on garbage.
    A faulty sensor emitting 'ERR', a blank, or text where a number is expected
    is treated as 'missing' (returns the default) rather than raising — a single
    bad value must never take down the detection pipeline. Non-numeric lookups
    that aren't being compared (e.g. status strings) still come back raw via raw().
    """
    def __init__(self, metrics: dict):
        self._m = metrics

    def get(self, key, default=0):
        v = self._m.get(key, default)
        if isinstance(v, (int, float)):
            return v
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    def raw(self, key, default=None):
        return self._m.get(key, default)


def detect(r: Reading) -> list[Anomaly]:
    """Run all applicable detectors for one reading."""
    out: list[Anomaly] = []
    m = _NumSafe(r.metrics)

    # --- Solar inverter: zero output while irradiance is high => likely trip ---
    if r.asset_type == "SolarInverter":
        if m.get("irradiance_wm2", 0) > 400 and m.get("power_kw", 0) <= 0.5:
            out.append(_mk(r, "inverter_no_output",
                           f"Irradiance {m.get('irradiance_wm2')} W/m² but output "
                           f"{m.get('power_kw')} kW — inverter likely tripped or offline."))
        if m.get("temp_c", 0) >= 75:
            out.append(_mk(r, "inverter_overtemp",
                           f"Inverter temperature {m.get('temp_c')}°C exceeds safe threshold."))
        # Performance Ratio: actual vs. what irradiance + rating say to expect.
        pr = performance_ratio(r)
        if pr is not None and 0 < pr < PR_ALERT_THRESHOLD and m.get("power_kw", 0) > 0.5:
            out.append(_mk(r, "inverter_low_pr",
                           f"Performance ratio {pr:.2f} below {PR_ALERT_THRESHOLD:.2f} "
                           f"(actual {m.get('power_kw')} kW vs expected "
                           f"{expected_power_kw(r):.0f} kW) — partial underperformance."))

    # --- Solar string: DC voltage far below array neighbours => open/failed string ---
    if r.asset_type == "SolarString":
        if m.get("dc_voltage", 0) < m.get("expected_dc_voltage", 1) * 0.7:
            out.append(_mk(r, "string_undervoltage",
                           f"String DC voltage {m.get('dc_voltage')} V vs expected "
                           f"~{m.get('expected_dc_voltage')} V — possible module/connector fault."))

    # --- Wind turbine: high wind but low power => pitch/yaw or curtailment issue ---
    if r.asset_type == "WindTurbine":
        if m.get("wind_ms", 0) > 8 and m.get("power_kw", 0) < m.get("rated_kw", 1e9) * 0.2:
            out.append(_mk(r, "turbine_underperform",
                           f"Wind {m.get('wind_ms')} m/s but output "
                           f"{m.get('power_kw')} kW — underperforming vs rating."))
        if m.get("gearbox_temp_c", 0) >= 80:
            out.append(_mk(r, "gearbox_overtemp",
                           f"Gearbox temperature {m.get('gearbox_temp_c')}°C is high."))
        if m.get("vibration_mm_s", 0) >= 7:
            out.append(_mk(r, "turbine_vibration",
                           f"Nacelle vibration {m.get('vibration_mm_s')} mm/s above alarm level."))

    # --- Transformer: temperature / loading ---
    if r.asset_type == "Transformer":
        if m.get("oil_temp_c", 0) >= 90:
            out.append(_mk(r, "transformer_overtemp",
                           f"Transformer oil temperature {m.get('oil_temp_c')}°C is critical."))
        if m.get("load_pct", 0) >= 110:
            out.append(_mk(r, "transformer_overload",
                           f"Transformer loaded at {m.get('load_pct')}% of rating."))

    # --- Tracker: stuck vs commanded angle ---
    if r.asset_type == "Tracker":
        if abs(m.get("angle_deg", 0) - m.get("target_deg", 0)) >= 15:
            out.append(_mk(r, "tracker_misalign",
                           f"Tracker at {m.get('angle_deg')}° vs target "
                           f"{m.get('target_deg')}° — possible motor/jam fault."))

    # --- Meter: communication loss (stale/blank) ---
    if r.asset_type == "Meter":
        if m.get("comm_ok", 1) == 0:
            out.append(_mk(r, "meter_comm_loss",
                           "Meter communication lost — no telemetry received."))

    return out


# ---------------------------------------------------------------------------
# Performance Ratio (PR) — expected vs. actual, the KPI every solar engineer
# tracks. Far stronger than a fixed kW threshold because it self-adjusts to
# how much sun there actually is.
# ---------------------------------------------------------------------------
def expected_power_kw(r: Reading) -> float | None:
    """Expected AC power from irradiance and nameplate rating (simplified)."""
    m = _NumSafe(r.metrics)
    irr = m.get("irradiance_wm2", 0)
    rated = m.get("rated_kw", 0)
    if not irr or not rated:
        return None
    # Linear model: at STC irradiance the asset makes its rated power.
    return rated * (irr / STC_IRRADIANCE)


def performance_ratio(r: Reading) -> float | None:
    """PR = actual / expected. ~1.0 is healthy; well below flags loss."""
    exp = expected_power_kw(r)
    if not exp or exp <= 0:
        return None
    return _NumSafe(r.metrics).get("power_kw", 0) / exp


# ---------------------------------------------------------------------------
# Fleet detector: peer comparison. An asset producing far less than its
# healthy siblings is suspicious even if it's above every fixed threshold —
# this is where silent 5-15% money leaks hide.
# ---------------------------------------------------------------------------
def detect_fleet(readings: list[Reading]) -> list[Anomaly]:
    """
    Compare each inverter against the median of its peers (same asset_type).
    Flags any asset producing <= PEER_UNDERPERF_RATIO of the peer median.
    """
    out: list[Anomaly] = []
    # Group inverters that are actually producing (ignore fully-offline ones;
    # those are caught by the no-output detector, not peer comparison).
    invs = [r for r in readings
            if r.asset_type == "SolarInverter"
            and _NumSafe(r.metrics).get("power_kw", 0) > 0.5]
    if len(invs) < 3:
        return out  # need a few peers for a meaningful median

    powers = [_NumSafe(r.metrics).get("power_kw", 0) for r in invs]
    peer_median = median(powers)
    if peer_median <= 0:
        return out

    for r in invs:
        p = _NumSafe(r.metrics).get("power_kw", 0)
        ratio = p / peer_median
        if ratio <= PEER_UNDERPERF_RATIO:
            a = _mk(r, "inverter_peer_underperform",
                    f"{r.asset_id} at {p:.0f} kW is {ratio*100:.0f}% of the peer "
                    f"median ({peer_median:.0f} kW) — underperforming vs healthy siblings.")
            # stash peer median so the pipeline can surface it on the work item
            a.metrics["_peer_median_kw"] = round(peer_median, 1)
            out.append(a)
    return out
