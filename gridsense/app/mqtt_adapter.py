"""
MQTT Adapter — GridSense Phase 2 (Option E)

Subscribes to an MQTT broker and forwards telemetry to the GridSense REST API.
This is the bridge between real IoT hardware (or the MQTT simulator) and the platform.

Topic format:
  gridsense/<tenant_id>/<asset_type>/<asset_id>
  e.g. gridsense/aerowind/SolarInverter/INV-01

Payload (JSON):
  { "power_kw": 45.2, "temp_c": 52.1, "irradiance_wm2": 850.0, ... }
"""
import os
import json
import time
import requests
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

MQTT_BROKER   = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT     = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC    = os.getenv("MQTT_TOPIC", "gridsense/#")
INGEST_URL    = os.getenv("GRIDSENSE_INGEST_URL", "http://web:5000/api/v2/ingest")
API_KEY       = os.getenv("GRIDSENSE_API_KEY", "key-aerowind")

BATCH: list   = []
BATCH_INTERVAL = 2  # seconds between flushes


def flush_batch():
    global BATCH
    if not BATCH:
        return
    to_send = BATCH[:]
    BATCH = []

    # Group records by tenant
    by_tenant = {}
    for rec in to_send:
        tid = rec.pop("tenant_id", "aerowind")
        by_tenant.setdefault(tid, []).append(rec)

    for tid, recs in by_tenant.items():
        api_key = f"key-{tid}"  # Phase 3 mapping convention
        try:
            r = requests.post(
                INGEST_URL, json=recs,
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                timeout=5
            )
            print(f"[MQTT→API] Flushed {len(recs)} records for {tid} → HTTP {r.status_code}")
        except Exception as e:
            print(f"[MQTT→API] Flush failed for {tid}: {e}")


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[MQTT] Connected to broker {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        print(f"[MQTT] Subscribed to {MQTT_TOPIC}")
    else:
        print(f"[MQTT] Connection failed, rc={rc}")


def on_message(client, userdata, msg):
    """Parse MQTT topic+payload into a telemetry record and queue it."""
    try:
        # Topic: gridsense/<tenant_id>/<asset_type>/<asset_id>
        parts = msg.topic.split("/")
        if len(parts) < 4:
            return
        _, tenant_id, asset_type, asset_id = parts[0], parts[1], parts[2], parts[3]

        payload = json.loads(msg.payload.decode("utf-8"))
        record = {
            "tenant_id":  tenant_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "asset_id":   asset_id,
            "asset_type": asset_type,
            "metrics":    payload,
        }
        BATCH.append(record)
    except Exception as e:
        print(f"[MQTT] Message parse error on topic {msg.topic}: {e}")


def main():
    print("=== GridSense MQTT Adapter ===")
    print(f"Broker : {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Topic  : {MQTT_TOPIC}")
    print(f"Ingest : {INGEST_URL}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    # Retry connection until broker is ready (useful on docker startup)
    for attempt in range(10):
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            break
        except Exception as e:
            print(f"[MQTT] Broker not ready (attempt {attempt+1}/10): {e}")
            time.sleep(3)

    client.loop_start()

    # Flush accumulated messages every BATCH_INTERVAL seconds
    try:
        while True:
            time.sleep(BATCH_INTERVAL)
            flush_batch()
    except KeyboardInterrupt:
        print("[MQTT] Shutting down adapter")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
