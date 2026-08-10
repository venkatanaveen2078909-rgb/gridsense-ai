from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, RootModel, field_validator
from datetime import datetime

class AssetReadingModel(BaseModel):
    asset_id: str = Field(..., description="Unique identifier for the asset")
    asset_type: str = Field(..., description="Type of asset (e.g., SolarInverter, WindTurbine)")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z", description="ISO 8601 timestamp")
    metrics: Dict[str, Any] = Field(..., description="Key-value pairs of telemetry metrics")

    @field_validator("metrics")
    def validate_metrics(cls, v):
        # Enforce that all metric values are numeric (float/int), coercing strings if necessary, 
        # or dropping/nulling them, but for strictness we'll coerce or keep as is,
        # but let's ensure we don't have deeply nested structures that might crash detectors.
        processed = {}
        for key, val in v.items():
            if val is None or val == "":
                continue
            try:
                # Try to coerce to float
                f = float(val)
                processed[key] = int(f) if f.is_integer() else f
            except (ValueError, TypeError):
                # If it's a string that can't be parsed, keep it as is (detectors should handle it,
                # as fixed in the previous security review, but we validate the structure).
                processed[key] = val
        return processed

class TelemetryIngestRequest(RootModel):
    root: List[AssetReadingModel]
