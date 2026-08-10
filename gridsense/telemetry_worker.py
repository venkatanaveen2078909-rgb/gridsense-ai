"""
Phase 2 Telemetry Worker (Replaces monitor_daemon.py)
Reads from Redis Queue instead of SQLite table.
Writes to PostgreSQL TimescaleDB.
"""
from __future__ import annotations
import time
import json
import os
import signal
import sys
from datetime import datetime, timezone, timedelta
import redis

# Ensure project root is on path when running directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db
from app.schema import Reading, PlantContext
from app.pipeline import detect_all
from app.agent import OMAgent, build_workitem
from app.logging_config import get_logger

log = get_logger("telemetry_worker")

# --- Configuration ---
COOLDOWN_SECONDS      = int(os.getenv("GRIDSENSE_COOLDOWN_S", str(15 * 60)))
TELEMETRY_TTL_HOURS   = int(os.getenv("GRIDSENSE_TELEMETRY_TTL_H", "48"))
REDIS_URL             = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# --- Graceful shutdown ---
_shutdown = False

def _handle_signal(signum, frame):
    global _shutdown
    log.info("Shutdown signal received, stopping after current cycle",
             extra={"signal": signum})
    _shutdown = True

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT,  _handle_signal)

def _archive_old_telemetry(conn):
    """Delete processed telemetry older than TELEMETRY_TTL_HOURS."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=TELEMETRY_TTL_HOURS)).isoformat()
    result = conn.execute(
        "DELETE FROM telemetry WHERE timestamp < %s", (cutoff,)
    )
    # Using cu.rowcount for psycopg2
    rc = conn.cu.rowcount if hasattr(conn, 'cu') else 0
    if rc:
        log.info("Archived old telemetry", extra={"deleted_rows": rc, "older_than": cutoff})

def process_payload(tenant_id: str, payload: list, agent: OMAgent, conn) -> int:
    # 0. Read Plant Context for this specific tenant
    state = conn.execute("SELECT * FROM plant_state WHERE tenant_id = %s", (tenant_id,)).fetchone()
    if state:
        assets_in_maintenance = state["assets_in_maintenance"]
        if isinstance(assets_in_maintenance, str):
            assets_in_maintenance = json.loads(assets_in_maintenance)
        ctx = PlantContext(
            grid_available=bool(state["grid_available"]),
            plant_status=state["plant_status"],
            assets_in_maintenance=assets_in_maintenance
        )
    else:
        ctx = PlantContext(grid_available=True, plant_status="RUNNING", assets_in_maintenance=[])

    # 1. Deduplicate latest reading per asset from the payload
    latest_by_asset = {}
    db_rows = []
    
    for item in payload:
        aid = item.get("asset_id")
        latest_by_asset[aid] = item
        db_rows.append({
            "tenant_id": tenant_id,
            "timestamp": item.get("timestamp"),
            "asset_id": aid,
            "asset_type": item.get("asset_type"),
            "metrics_json": json.dumps(item.get("metrics", {}))
        })
        
    # Write incoming telemetry to postgres (historian)
    if db_rows:
        conn.cu.executemany(
            "INSERT INTO telemetry (tenant_id, timestamp, asset_id, asset_type, metrics_json, processed) VALUES (%(tenant_id)s, %(timestamp)s, %(asset_id)s, %(asset_type)s, %(metrics_json)s, TRUE)",
            db_rows
        )

    readings = [
        Reading(
            asset_id=r.get("asset_id"),
            asset_type=r.get("asset_type"),
            timestamp=r.get("timestamp"),
            metrics=r.get("metrics", {})
        )
        for r in latest_by_asset.values()
    ]

    if not readings:
        return 0

    # 2. Run deterministic rule engine
    anomalies = detect_all(readings, ctx)
    detected_keys = {(a.asset_id, a.rule) for a in anomalies}

    now_str = datetime.now(timezone.utc).isoformat()
    now_dt  = datetime.now(timezone.utc)

    # 3. Resolve incidents that no longer have a matching anomaly
    active_incidents = conn.execute(
        "SELECT * FROM incidents WHERE tenant_id = %s AND status = 'Active'", (tenant_id,)
    ).fetchall()
    for inc in active_incidents:
        key = (inc["asset_id"], inc["rule"])
        if key not in detected_keys:
            conn.execute(
                "UPDATE incidents SET status = 'Resolved', last_seen = %s WHERE id = %s",
                (now_str, inc["id"])
            )
            log.info("Incident resolved", extra={
                "tenant_id": tenant_id, "asset_id": key[0], "rule": key[1], "incident_id": inc["id"]
            })

    # 4. Create/update incidents and trigger AI triage when not in cooldown
    for a in anomalies:
        key = (a.asset_id, a.rule)

        # Find or create an active incident
        conn.execute(
            "SELECT * FROM incidents WHERE tenant_id = %s AND asset_id = %s AND rule = %s AND status = 'Active'",
            (tenant_id,) + key
        )
        inc = conn.fetchone()

        if inc:
            inc_id = inc["id"]
            conn.execute(
                "UPDATE incidents SET last_seen = %s WHERE id = %s", (now_str, inc_id)
            )
        else:
            conn.execute(
                "INSERT INTO incidents (tenant_id, asset_id, asset_type, rule, status, first_seen, last_seen)"
                " VALUES (%s, %s, %s, %s, 'Active', %s, %s) RETURNING id",
                (tenant_id, a.asset_id, a.asset_type, a.rule, now_str, now_str)
            )
            res = conn.fetchone()
            inc_id = res["id"] if res else 0
            log.info("New incident opened", extra={
                "tenant_id": tenant_id, "asset_id": a.asset_id, "rule": a.rule, "incident_id": inc_id
            })

        # Check 15-minute AI cooldown
        conn.execute(
            "SELECT created_at FROM work_orders"
            " WHERE asset_id = %s AND rule = %s ORDER BY created_at DESC LIMIT 1",
            key
        )
        last_wo = conn.fetchone()

        run_ai = False
        if not last_wo:
            run_ai = True
        else:
            ts = last_wo["created_at"]
            if isinstance(ts, str):
                last_wo_dt = datetime.fromisoformat(ts)
            else:
                last_wo_dt = ts
            if (now_dt - last_wo_dt).total_seconds() > COOLDOWN_SECONDS:
                run_ai = True

        if run_ai:
            log.info("Triggering AI triage", extra={
                "asset_id": a.asset_id, "rule": a.rule
            })
            try:
                    wo = build_workitem(a, agent)
                    wo_json = json.dumps(wo.to_dict())
                    conn.execute(
                        "INSERT INTO work_orders"
                        " (id, tenant_id, incident_id, asset_id, rule, severity, action, confidence, data_json, created_at)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (wo.work_id, tenant_id, inc_id, a.asset_id, a.rule,
                         wo.severity, wo.action, wo.confidence, wo_json, now_str)
                    )
                    conn.execute(
                        "UPDATE incidents SET work_order_id = %s WHERE id = %s",
                        (wo.work_id, inc_id)
                    )
                    log.info("Work order created", extra={
                        "tenant_id": tenant_id, "work_id": wo.work_id,
                        "severity": wo.severity, "asset_id": a.asset_id, "action": wo.action
                    })
            except Exception as e:
                    log.error("AI triage failed", extra={
                        "tenant_id": tenant_id, "asset_id": a.asset_id, "rule": a.rule, "error": str(e)
                    })

    # 5. Archive old telemetry occasionally (maybe only every 100 cycles to save DB queries)
    # Passed to caller

    return len(db_rows)

def main():
    log.info("Telemetry worker starting", extra={
        "cooldown_s": COOLDOWN_SECONDS,
        "telemetry_ttl_h": TELEMETRY_TTL_HOURS
    })
    
    agent = OMAgent()
    
    # Initialize redis
    try:
        redis_client = redis.from_url(REDIS_URL)
        redis_client.ping()
        log.info("Connected to Redis")
    except Exception as e:
        log.error("Failed to connect to Redis", extra={"error": str(e)})
        sys.exit(1)
        
    cycle = 0

    while not _shutdown:
        try:
            # Block for up to 1 second waiting for telemetry
            item = redis_client.blpop("telemetry_queue", timeout=1)
            if item:
                _, payload_bytes = item
                envelope = json.loads(payload_bytes)
                tenant_id = envelope.get("tenant_id", "unknown")
                readings  = envelope.get("readings", [])
                
                with get_db() as conn:
                    processed = process_payload(tenant_id, readings, agent, conn)
                    cycle += 1
                    
                    if cycle % 100 == 0:
                        _archive_old_telemetry(conn)
                        
                    conn.commit()
        except Exception as e:
            log.error("Unhandled error in worker cycle", extra={"error": str(e)})
            time.sleep(1)

    log.info("Telemetry worker stopped cleanly")

if __name__ == "__main__":
    main()
