"""
Configuration for GRIDSENSE — a renewable-energy O&M triage agent.

Generic, original code. No proprietary data or processes: it works on
synthetic/CSV telemetry and public-style asset definitions.
"""
from __future__ import annotations
import os

# Load .env file automatically (safe: does nothing if file doesn't exist)
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)  # override=False: real env vars take priority
except ImportError:
    pass  # python-dotenv not installed — rely on shell env vars

ANTHROPIC_MODEL = os.getenv("GRIDSENSE_MODEL", "claude-haiku-4-5")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MAX_TOKENS = 1200

# --- Groq settings (free alternative to Claude) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL   = os.getenv("GRIDSENSE_GROQ_MODEL", "llama-3.3-70b-versatile")

# --- OpenRouter settings (OpenAI-compatible, many models) ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# --- Dashboard API security ---
# Set GRIDSENSE_API_KEY to a random secret to enable API key auth.
# Leave blank / unset to run without auth (development only).
GRIDSENSE_API_KEY = os.getenv("GRIDSENSE_API_KEY", "")

# Fault severity bands for O&M prioritisation.
SEVERITIES = ["Critical", "High", "Medium", "Low", "Informational"]

# Recommended dispatch action categories (what the agent proposes; a human approves).
ACTIONS = [
    "DispatchTechnician",   # send a crew now
    "RemoteReset",          # try a remote/automated recovery first
    "ScheduleMaintenance",  # add to the maintenance queue
    "MonitorOnly",          # watch, no action yet
    "RaiseTicketOnly",      # log for records, no field response
]

# Asset types this agent understands (solar + wind + shared electrical).
ASSET_TYPES = ["SolarInverter", "SolarString", "WindTurbine", "Transformer", "Meter", "Tracker"]

# --- Financial impact (speak the language of plant owners, not JSON) ---
# Feed-in / PPA tariff used to convert lost energy into money.
TARIFF_PER_KWH = float(os.getenv("GRIDSENSE_TARIFF", "5.2"))   # INR per kWh
CURRENCY = os.getenv("GRIDSENSE_CURRENCY", "INR")

# --- Performance Ratio (PR) and peer-comparison tuning ---
# PR = actual output / expected output (from irradiance + rated capacity).
# Below this PR on a healthy-irradiance reading, we flag underperformance.
PR_ALERT_THRESHOLD = float(os.getenv("GRIDSENSE_PR_ALERT", "0.80"))
# A peer is "underperforming" if it produces this fraction (or less) of the
# median of its healthy siblings — catches silent 5-15% losses a fixed
# threshold would miss entirely.
PEER_UNDERPERF_RATIO = float(os.getenv("GRIDSENSE_PEER_RATIO", "0.85"))
# Standard-Test-Condition reference irradiance for PR maths.
STC_IRRADIANCE = 1000.0  # W/m²
