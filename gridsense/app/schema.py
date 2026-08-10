"""
Shared data structures for the O&M triage pipeline.

Flow:  raw telemetry rows -> detected Anomaly -> AI-triaged WorkItem
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class Reading:
    """One telemetry sample for one asset."""
    asset_id: str
    asset_type: str
    timestamp: str
    metrics: dict            # e.g. {"power_kw": 0.0, "dc_voltage": 812, "temp_c": 71}


@dataclass
class PlantContext:
    """
    Plant-wide state used as GUARD CONDITIONS before raising an alert.
    This is the reviewer's key point: 'bright sun + zero output' is only a
    fault if the plant is actually running, the grid is up, and the asset
    isn't in maintenance. Without these guards, false positives explode.
    """
    grid_available: bool = True
    plant_status: str = "RUNNING"        # RUNNING | CURTAILED | SHUTDOWN
    assets_in_maintenance: tuple = ()    # asset_ids under a maintenance ticket

    def is_suppressed(self, asset_id: str) -> str | None:
        """Return a reason to suppress an alert, or None if it should proceed."""
        if not self.grid_available:
            return "grid unavailable (plant-wide) — output loss expected"
        if self.plant_status == "SHUTDOWN":
            return "plant in planned shutdown"
        if self.plant_status == "CURTAILED":
            return "plant curtailed by grid operator — reduced output expected"
        if asset_id in self.assets_in_maintenance:
            return "asset under an open maintenance ticket"
        return None


@dataclass
class Anomaly:
    """A rule-detected deviation, before the agent reasons about it."""
    asset_id: str
    asset_type: str
    timestamp: str
    rule: str                # which detector fired
    detail: str              # human-readable description of the deviation
    metrics: dict            # the metrics snapshot that triggered it


@dataclass
class WorkItem:
    """The agent's triaged output — what an O&M lead would act on."""
    work_id: str
    created_at: str
    asset_id: str
    asset_type: str

    severity: str            # Critical|High|Medium|Low|Informational
    action: str              # recommended action category
    confidence: float
    title: str               # one-line summary for the queue
    likely_cause: str        # the agent's top diagnosis
    recommended_steps: list  # ordered, concrete steps for the crew
    est_energy_loss_kwh: Optional[float] = None  # if the agent can estimate it

    # --- probabilistic root cause (reviewer: rank causes, don't declare one) ---
    probable_causes: list = field(default_factory=list)  # [{"cause":..,"probability":0-1}]

    # --- performance context (reviewer: PR + peer comparison are core) ---
    performance_ratio: Optional[float] = None   # actual / expected, 0..1+
    peer_median_kw: Optional[float] = None      # median of healthy siblings

    # --- financial impact (reviewer: speak money, not JSON) ---
    est_revenue_loss: Optional[float] = None    # per-event, in CURRENCY
    currency: str = "INR"

    needs_human_approval: bool = True   # agent proposes; human dispatches
    reasoning: str = ""                 # rationale for the audit trail
    source_rule: str = ""               # which detector surfaced it

    @staticmethod
    def new_id() -> str:
        return "WO-" + uuid.uuid4().hex[:8].upper()

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)
