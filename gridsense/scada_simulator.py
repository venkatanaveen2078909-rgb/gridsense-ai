import time
import csv
import json
import os
import random
import requests
from datetime import datetime, timezone

SAMPLE_CSV = os.path.join(os.path.dirname(__file__), "samples", "plant_telemetry.csv")
INGEST_URL = os.getenv("GRIDSENSE_INGEST_URL", "http://127.0.0.1:5000/api/v2/ingest")
API_KEY = os.getenv("GRIDSENSE_API_KEY", "key-aerowind")  # Phase 3: use tenant API key

def read_base_telemetry():
    rows = []
    with open(SAMPLE_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            asset_id = row.pop('asset_id')
            asset_type = row.pop('asset_type')
            row.pop('timestamp', None)
            
            metrics = {}
            for k, v in row.items():
                if not v: continue
                try:
                    metrics[k] = float(v)
                except ValueError:
                    metrics[k] = v
            
            rows.append({
                "asset_id": asset_id,
                "asset_type": asset_type,
                "metrics": metrics
            })
    return rows

def generate_live_data(base_rows):
    now = datetime.now(timezone.utc).isoformat()
    new_rows = []
    
    for base in base_rows:
        metrics = base["metrics"].copy()
        
        for k, v in metrics.items():
            if isinstance(v, float) or isinstance(v, int):
                jitter = v * random.uniform(-0.02, 0.02)
                metrics[k] = round(v + jitter, 2)
                
        new_rows.append({
            "timestamp": now,
            "asset_id": base["asset_id"],
            "asset_type": base["asset_type"],
            "metrics": metrics
        })
        
    return new_rows

def insert_telemetry(rows):
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    try:
        res = requests.post(INGEST_URL, json=rows, headers=headers, timeout=5)
        res.raise_for_status()
    except Exception as e:
        print(f"Failed to post telemetry: {e}")

if __name__ == "__main__":
    print("Starting SCADA Simulator (Phase 2)...")
    base_rows = read_base_telemetry()
    print(f"Loaded {len(base_rows)} baseline assets. Pushing live data to {INGEST_URL} every 2s...")
    
    try:
        while True:
            live_data = generate_live_data(base_rows)
            insert_telemetry(live_data)
            print(f"[{datetime.now().isoformat()}] Sent {len(live_data)} telemetry records to API.")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nSCADA Simulator stopped.")
