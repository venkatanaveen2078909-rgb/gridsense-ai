"""
MQTT Simulator — GridSense Phase 2 (Option E)

Publishes synthetic solar/wind telemetry to the MQTT broker.
This demonstrates real IoT message patterns and replaces the HTTP-based SCADA simulator
for the MQTT pipeline. Both can run simultaneously.

Topic format: gridsense/<tenant_id>/<asset_type>/<asset_id>
"""
import os
import csv
import json
import time
import random
import paho.mqtt.client as mqtt
from datetime import datetime, timezone

MQTT_BROKER = os.getenv("MQTT_BROKER", "mosquitto")
MQTT_PORT   = int(os.getenv("MQTT_PORT", "1883"))
TENANT_ID   = os.getenv("MQTT_TENANT_ID", "aerowind")
SAMPLE_CSV  = os.path.join(os.path.dirname(__file__), "samples", "plant_telemetry.csv")
INTERVAL_S  = float(os.getenv("MQTT_INTERVAL_S", "3"))


def read_base_telemetry():
    rows = []
    with open(SAMPLE_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            asset_id   = row.pop("asset_id")
            asset_type = row.pop("asset_type")
            row.pop("timestamp", None)
            metrics = {}
            for k, v in row.items():
                if not v:
                    continue
                try:
                    metrics[k] = float(v)
                except ValueError:
                    metrics[k] = v
            rows.append({"asset_id": asset_id, "asset_type": asset_type, "metrics": metrics})
    return rows


def jitter(val: float, pct: float = 0.03) -> float:
    return round(val * (1 + random.uniform(-pct, pct)), 3)


def generate_live_data(base_rows):
    return [
        {
            "asset_id":   r["asset_id"],
            "asset_type": r["asset_type"],
            "metrics":    {k: jitter(v) if isinstance(v, float) else v for k, v in r["metrics"].items()},
        }
        for r in base_rows
    ]


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[MQTT-SIM] Connected to {MQTT_BROKER}:{MQTT_PORT}")
    else:
        print(f"[MQTT-SIM] Connection failed rc={rc}")


def main():
    print("=== GridSense MQTT Simulator ===")
    print(f"Broker  : {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Tenant  : {TENANT_ID}")
    print(f"Interval: {INTERVAL_S}s")

    base_rows = read_base_telemetry()
    print(f"Loaded {len(base_rows)} baseline assets")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect

    for attempt in range(10):
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            break
        except Exception as e:
            print(f"[MQTT-SIM] Broker not ready (attempt {attempt+1}/10): {e}")
            time.sleep(3)

    client.loop_start()

    try:
        while True:
            records = generate_live_data(base_rows)
            for tenant in ["aerowind", "solaris"]:
                for rec in records:
                    # Filter assets by tenant
                    at = rec["asset_type"]
                    if tenant == "aerowind" and at in ("SolarInverter", "SolarString", "Tracker"):
                        continue
                    if tenant == "solaris" and at in ("WindTurbine",):
                        continue
                        
                    topic   = f"gridsense/{tenant}/{rec['asset_type']}/{rec['asset_id']}"
                    payload = json.dumps(rec["metrics"])
                    client.publish(topic, payload, qos=1)
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            print(f"[{ts}] Published records via MQTT (filtered per tenant)")
            time.sleep(INTERVAL_S)
    except KeyboardInterrupt:
        print("[MQTT-SIM] Shutting down simulator")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
