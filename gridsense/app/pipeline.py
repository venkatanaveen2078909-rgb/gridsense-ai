"""
Pipeline: telemetry CSV -> detect anomalies -> agent triage -> work orders.

CSV format (one row per reading). Columns:
  asset_id, asset_type, timestamp, <metric columns...>
Any extra columns become numeric metrics automatically.
"""
from __future__ import annotations
import csv
import json
import os
from datetime import datetime, timezone

from .schema import Reading, WorkItem, PlantContext
from .detectors import detect, detect_fleet, performance_ratio
from .agent import OMAgent, build_workitem
from .cmms import CMMSProvider, FileCMMSProvider

WORKORDER_LOG = os.getenv("GRIDSENSE_LOG", "gridsense_workorders.jsonl")

_META_COLS = {"asset_id", "asset_type", "timestamp"}


def _coerce(v: str):
    """Turn a CSV cell into int/float where possible, else leave as string."""
    if v is None or v == "":
        return None
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except ValueError:
        return v


def read_telemetry(csv_path: str) -> list[Reading]:
    readings: list[Reading] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            metrics = {k: _coerce(v) for k, v in row.items() if k not in _META_COLS}
            readings.append(Reading(
                asset_id=row["asset_id"],
                asset_type=row["asset_type"],
                timestamp=row.get("timestamp", ""),
                metrics=metrics,
            ))
    return readings


def _log(item: WorkItem, cmms: CMMSProvider = None) -> None:
    if cmms is None:
        cmms = FileCMMSProvider(WORKORDER_LOG)
    cmms.dispatch_workorder(item)


def detect_all(readings: list[Reading], ctx: PlantContext | None = None) -> list:
    """
    Run per-reading detectors AND the fleet peer-comparison detector, then
    apply plant-level GUARD CONDITIONS so we don't alert on losses that the
    plant state already explains (grid down, curtailment, maintenance).
    """
    ctx = ctx or PlantContext()
    reading_by_id = {r.asset_id: r for r in readings}

    raw = [a for r in readings for a in detect(r)]
    raw += detect_fleet(readings)

    kept = []
    for a in raw:
        reason = ctx.is_suppressed(a.asset_id)
        if reason:
            continue  # guard condition explains the deviation; don't cry wolf
        # attach PR to the anomaly so the work item can display it
        r = reading_by_id.get(a.asset_id)
        if r is not None:
            pr = performance_ratio(r)
            if pr is not None:
                a.metrics["_performance_ratio"] = round(pr, 2)
        kept.append(a)
    return kept


def process_file(csv_path: str, agent: OMAgent | None = None,
                 ctx: PlantContext | None = None,
                 cmms: CMMSProvider | None = None) -> list[WorkItem]:
    """Full run: ingest CSV, detect, triage each anomaly, persist work orders."""
    readings = read_telemetry(csv_path)
    anomalies = detect_all(readings, ctx)
    if agent is None:
        agent = OMAgent()
    items: list[WorkItem] = []
    for a in anomalies:
        item = build_workitem(a, agent)
        _log(item, cmms)
        items.append(item)
    return items


def scan_only(csv_path: str, ctx: PlantContext | None = None) -> list:
    """Run all detectors (no AI, no key) — useful to preview candidates."""
    return detect_all(read_telemetry(csv_path), ctx)
