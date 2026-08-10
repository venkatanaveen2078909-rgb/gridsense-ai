<div align="center">

⚡ GridSense

AI-Powered Context-Aware SCADA Intelligence for Renewable Energy

Detect the signal. Understand the context. Act on what matters.

<p>
  <a href="https://github.com/venkatanaveen2078909-rgb/gridsense-ai">
    <img src="https://img.shields.io/badge/Project-GridSense-0A0A0A?style=for-the-badge&logo=github" alt="GridSense">
  </a>
  <img src="https://img.shields.io/github/license/venkatanaveen2078909-rgb/gridsense-ai?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/github/stars/venkatanaveen2078909-rgb/gridsense-ai?style=for-the-badge" alt="Stars">
  <img src="https://img.shields.io/github/last-commit/venkatanaveen2078909-rgb/gridsense-ai?style=for-the-badge" alt="Last Commit">
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/MQTT-Telemetry-660066?style=flat-square&logo=mqtt&logoColor=white" alt="MQTT">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/AI-LLM%20Triage-8B5CF6?style=flat-square" alt="AI">
  <img src="https://img.shields.io/badge/SCADA-Intelligence-00A67E?style=flat-square" alt="SCADA">
</p>

<p>
  <a href="#-why-gridsense">Why GridSense</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-key-capabilities">Capabilities</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-demo">Demo</a> •
  <a href="#-architecture">Architecture</a>
</p>

</div>

🚨 The Problem

Renewable-energy control rooms don't suffer from a lack of data.

They suffer from too much uncontextualised data.

A single grid event can cascade into hundreds of downstream alarms:

                    GRID EVENT
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
       Inverter       Transformer   Meter
       Alarm × N      Alarm × N     Alarm × N
          │             │             │
          └─────────────┼─────────────┘
                        ▼
                 🔴 ALARM FLOOD
                        │
                        ▼
               Operator investigates
               hundreds of symptoms
                        │
                        ▼
                  Higher MTTR

Traditional SCADA tells operators what changed.

GridSense helps them understand why.

⚡ Why GridSense?

GridSense is an AI-powered, context-aware SCADA intelligence layer that sits above existing telemetry infrastructure.

It combines:

Deterministic detection + contextual reasoning + human approval

to turn noisy telemetry into prioritised, explainable O&M decisions.

The core principle

┌─────────────────────┐
│      Telemetry      │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Deterministic RPA  │  ← Fast, cheap, explainable
│   Rule Detectors    │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Context Correlation │  ← Plant state + peer behaviour
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│     AI Agent        │  ← Diagnosis + prioritisation
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│   Work Order        │  ← Actionable recommendation
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│   Human Approval    │  ← Human stays in control
└─────────────────────┘

🎯 What GridSense Delivers

Capability

What it does

🔍 Fault Detection

Finds abnormal equipment behaviour from telemetry

☀️ Performance Ratio

Separates weather-driven production loss from genuine faults

📊 Peer Benchmarking

Finds subtle 5–15% underperformance against healthy peers

🧠 Context Awareness

Understands grid-down, curtailment and maintenance states

🤖 AI Triage

Ranks likely causes and recommends next actions

📝 Work Orders

Converts anomalies into structured maintenance responses

💰 Financial Impact

Estimates lost energy and configurable ₹ impact

👨‍🔧 Human-in-the-Loop

Requires approval before physical/dispatch actions

📜 Audit Trail

Records decisions and rationale for traceability

🧠 The Differentiator: Context-Aware Suppression

Consider a grid outage.

A traditional alarm system may see:

Grid Down
   │
   ├── Inverter 01 → 0 kW
   ├── Inverter 02 → 0 kW
   ├── Inverter 03 → 0 kW
   ├── Inverter 04 → 0 kW
   ├── ...
   └── Inverter 500 → 0 kW

GridSense understands the causal context:

                 GRID DOWN
                     │
                     ▼
             Plant unavailable
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
   Root event detected    Secondary symptoms
                                │
                                ▼
                    Suppress / correlate
                                │
                                ▼
                     ONE meaningful event

The operator sees the root event, not a wall of symptoms.

This is the core idea behind reducing alarm fatigue without blindly hiding alarms.

🤖 AI-Powered O&M Triage

When a meaningful anomaly is detected, GridSense packages the relevant telemetry and context for the AI agent.

The agent produces a structured work order:

{
  "severity": "HIGH",
  "action": "REMOTE_RESET",
  "likely_cause": "Inverter trip",
  "confidence": 0.55,
  "energy_loss_kwh": 420,
  "estimated_cost_inr": 2730,
  "needs_human_approval": true
}

Example reasoning

Candidate causes

Inverter trip        ████████████████████ 55%
Communication issue  ███████               20%
Grid event           █████                 15%
Other                ███                   10%

The model ranks possibilities instead of pretending uncertainty does not exist.

🔥 Key Capabilities

<details>
<summary><strong>1. Deterministic Rule Engine</strong></summary>

The first layer uses deterministic detectors for known operational conditions.

This provides:

Low latency

Predictable behaviour

Explainability

Low inference cost

Easy unit testing

AI is used where reasoning adds value — not for every telemetry point.

</details>

<details>
<summary><strong>2. Performance-Ratio Detection</strong></summary>

GridSense can estimate expected production using irradiance and asset rating and compare it with actual output.

This helps distinguish:

Low irradiance
     ↓
Expected lower output
     ↓
No unnecessary fault

from:

Healthy irradiance
     ↓
Unexpectedly low output
     ↓
Potential equipment fault

</details>

<details>
<summary><strong>3. Peer Benchmarking</strong></summary>

Instead of relying only on fixed thresholds, GridSense can compare an asset against healthy siblings.

Example:

Inverter A    99% of peer median   ✅
Inverter B   101% of peer median   ✅
Inverter C    97% of peer median   ✅
Inverter D    86% of peer median   ⚠️

This catches silent degradation that may never cross a conventional alarm threshold.

</details>

<details>
<summary><strong>4. Context-Aware Suppression</strong></summary>

GridSense can use plant state to explain otherwise suspicious telemetry.

Supported context examples:

Grid outage

Curtailment

Planned maintenance

Existing maintenance ticket

The goal is not to hide alarms. The goal is to distinguish root events from predictable downstream consequences.

</details>

<details>
<summary><strong>5. Financial Impact</strong></summary>

Technical faults are translated into an owner-facing impact:

Lost generation       420 kWh
Configured tariff     ₹6.50/kWh
Estimated impact      ₹2,730

This helps prioritise incidents by operational and financial significance.

</details>

<details>
<summary><strong>6. Human-in-the-Loop Safety</strong></summary>

GridSense follows a conservative operating model:

AI proposes
    ↓
System explains
    ↓
Human approves
    ↓
Action is dispatched

Physical interventions and crew dispatches require authorised human approval.

</details>

🌐 Supported Renewable Assets

Asset

Example intelligence

☀️ Solar Inverter

Trips, over-temperature, abnormal output

🔆 Solar String

Dead/low-output strings

🌬️ Wind Turbine

Underperformance, vibration

⚙️ Gearbox

Temperature anomalies

🔌 Transformer

Overload / thermal conditions

🛰️ Tracker

Stuck or abnormal tracking

📡 Meter

Communication loss

The detector architecture is extensible: new asset types and rules can be added without redesigning the entire pipeline.

🏗️ Architecture

flowchart LR
    A["SCADA / IoT Telemetry"] --> B["MQTT / CSV Ingest"]
    B --> C["Deterministic Rule Engine"]

    C -->|Normal| D["Continue Monitoring"]
    C -->|Anomaly| E["Context Builder"]

    E --> F["Plant State"]
    E --> G["Peer Behaviour"]
    E --> H["Telemetry Snapshot"]

    F --> I["AI Diagnostic Agent"]
    G --> I
    H --> I

    I --> J["Severity + Cause + Confidence"]
    J --> K["Work Order Builder"]
    K --> L{"Human Approval"}

    L -->|Approved| M["CMMS / Dispatch"]
    L -->|Rejected / Deferred| N["Review Queue"]

    K --> O["Audit Log"]

🔄 End-to-End Data Flow

Telemetry
   │
   ▼
┌─────────────────┐
│ MQTT / CSV      │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Rule Detectors  │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Context Engine  │
└────────┬────────┘
         ▼
┌─────────────────┐
│ AI Agent        │
│ Diagnosis       │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Work Order      │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Human Approval  │
└────────┬────────┘
         ▼
┌─────────────────┐
│ Audit / CMMS    │
└─────────────────┘

🖥️ Demo UI

GridSense is designed around an operations dashboard where an operator can move from:

Live telemetry → Active fault → AI diagnosis → Work order → Approval

Recommended dashboard flow

┌───────────────────────────────────────────────────────────┐
│ ⚡ GRIDSENSE                         🟢 SYSTEM OPERATIONAL │
├───────────────────┬───────────────────────────────────────┤
│ LIVE TELEMETRY    │  PLANT STATUS                        │
│                   │                                       │
│ Inverters   48    │  🟢 Grid Connected                   │
│ Turbines    12    │  ☀️ Generation: 84.2 MW              │
│ Transformers 4    │  ⚡ Availability: 97.8%               │
│                   │                                       │
├───────────────────┴───────────────────────────────────────┤
│ 🔴 ACTIVE FAULTS                                          │
│                                                           │
│ HIGH   INV-042   Inverter Trip       AI WORK ORDER        │
│ MED    TRK-017   Tracker Stuck       VIEW CONTEXT         │
│ LOW    MTR-008   Meter Comms Loss    REVIEW              │
├───────────────────────────────────────────────────────────┤
│ 🧠 CONTEXT                                               │
│ Grid: CONNECTED | Curtailment: OFF | Maintenance: 2      │
└───────────────────────────────────────────────────────────┘

Tip: Add a real dashboard screenshot or a short GIF under docs/assets/ when available. A 10–20 second demo GIF dramatically improves the repository's first impression.

🎬 Live Demo Story

The recommended 3-minute demo is:

01 — Detect

Show a real-time telemetry anomaly appearing in Active Faults.

02 — Diagnose

Click AI Work Order and show:

Severity

Likely cause

Confidence

Recommended action

Energy loss

Financial impact

03 — Demonstrate Context

Toggle:

GRID DOWN → ON

Show downstream zero-output alarms being correlated/suppressed.

04 — Restore

Toggle:

GRID DOWN → OFF

Show normal monitoring resume.

05 — Close

“GridSense doesn't just detect what's broken. It understands what matters.”

🚀 Quick Start

1. Clone

git clone https://github.com/venkatanaveen2078909-rgb/gridsense-ai.git
cd gridsense-ai

2. Create environment

Windows PowerShell

python -m venv .venv
.venv\Scripts\Activate.ps1

Linux / macOS

python -m venv .venv
source .venv/bin/activate

3. Install dependencies

pip install -r requirements.txt

4. Configure environment

Copy-Item .env.example .env

Linux / macOS:

cp .env.example .env

Add your required AI/API configuration to .env.

🔐 Never commit .env, API keys, tokens, credentials, or private certificates.

🧪 Run the Demo

Offline detection — no AI API required

python run.py --scan samples/plant_telemetry.csv

Full AI triage

python run.py --run samples/plant_telemetry.csv

Web dashboard

python web_app.py

Open:

http://127.0.0.1:5000

Offline verification

python tests/test_offline.py

🐳 Docker / MQTT

Start the supporting services:

docker compose up -d

Then run the telemetry simulator:

python mqtt_simulator.py

This provides a reproducible environment for demonstrating telemetry ingestion without requiring a connection to a real renewable-energy plant.

📁 Project Structure

gridsense-ai/
│
├── app/
│   ├── agent.py              # AI reasoning / triage
│   ├── pipeline.py           # Ingestion + work-order pipeline
│   ├── retry.py              # Retry utilities
│   └── schema.py             # Structured data models
│
├── mosquitto/
│   ├── data/                 # MQTT persistence
│   ├── log/                  # Broker logs
│   ├── samples/              # Sample telemetry
│   └── mosquitto.conf        # MQTT configuration
│
├── tests/                    # Offline tests
├── docker-compose.yml        # Local infrastructure
├── Dockerfile
├── mqtt_simulator.py         # Telemetry simulation
├── scada_simulator.py        # SCADA simulation
├── run.py                    # CLI entry point
├── web_app.py                # Dashboard
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md

🛡️ Safety & Governance

GridSense is an O&M decision-support system, not an autonomous plant-control system.

Safety rules

Principle

Behaviour

👨‍⚕️ Human approval

Physical actions require approval

🧠 Explainability

Decisions include rationale

📊 Evidence-based

Agent reasons only from supplied telemetry

🪜 Escalation

Prefer the cheapest safe action first

📜 Auditability

Work orders are logged

🔒 Secrets

Credentials remain outside source control

Example

Inverter trip
     │
     ▼
Remote reset possible?
   /       \
 YES       NO
  │         │
  ▼         ▼
Recommend  Technician
reset      inspection
  │         │
  └────┬────┘
       ▼
 Human approval

📈 Why This Matters

GridSense targets a practical operational problem:

More sensors
     ↓
More telemetry
     ↓
More alarms
     ↓
More operator workload

GridSense changes the flow:

More telemetry
     ↓
Deterministic filtering
     ↓
Context correlation
     ↓
AI reasoning
     ↓
Prioritised decisions
     ↓
Human-approved action

The outcome

⚡ Faster incident triage

🔕 Less alarm noise

🧑‍💻 Lower operator workload

🔧 Better maintenance prioritisation

💰 Visibility into financial impact

📋 Explainable work orders

🛡️ Safer human-controlled operations

🧩 Extending GridSense

Add a new fault

Add a detector to:

app/detectors.py

Return the project's standard anomaly structure and the downstream pipeline can process it.

Connect live SCADA

Replace or extend the sample CSV/MQTT ingestion layer with a historian or SCADA connector.

Connect a CMMS

Replace the local work-order logger with the target CMMS API.

Improve diagnosis

The reasoning layer can be upgraded independently from deterministic detection.

This separation keeps the system modular:

Detection ≠ Reasoning ≠ Dispatch

🧪 Demo Fault Matrix

Fault

Detection

AI Triage

Context

Financial Impact

Inverter trip

✅

✅

✅

✅

Inverter over-temperature

✅

✅

✅

✅

Dead solar string

✅

✅

✅

✅

Turbine underperformance

✅

✅

✅

✅

Gearbox overheating

✅

✅

✅

✅

Nacelle vibration

✅

✅

✅

✅

Transformer overload

✅

✅

✅

✅

Tracker stuck

✅

✅

✅

✅

Meter communication loss

✅

✅

✅

—

🧭 Roadmap

Deterministic telemetry detectors

Structured anomaly schema

AI-powered triage

Work-order generation

Human approval policy

Audit logging

MQTT telemetry simulation

Web dashboard

Live SCADA/historian connectors

CMMS integration

Multi-tenant plant management

Role-based access control

Advanced event correlation

Production observability

Plant-specific model evaluation

🏆 Hackathon / MSME Fit

GridSense is designed for the Power / Renewables / Electricals / Energy Efficiency space.

MSME opportunity

Smaller solar, wind, and C&I renewable operators may not have the resources for a large 24/7 monitoring team.

GridSense provides a lightweight intelligence layer:

        LOW-COST RULES
              +
       AI FOR JUDGEMENT
              +
       HUMAN APPROVAL
              │
              ▼
      O&M INTELLIGENCE

The architecture is intentionally designed so that AI is used for high-value reasoning, while deterministic logic handles the bulk of repetitive telemetry screening.

🔐 What GridSense Is — and Isn't

GridSense IS

An O&M triage prototype

A context-aware alarm intelligence layer

A deterministic + AI architecture

A work-order recommendation system

A human-in-the-loop decision-support system

GridSense IS NOT

A certified production SCADA controller

An autonomous safety system

A replacement for plant protection systems

A guarantee of diagnostic accuracy

Production deployment would require plant-specific validation, cybersecurity controls, operational acceptance testing, safety review, and integration with the target SCADA/historian and CMMS environments.

📚 Technical Design Principle

Rules detect. AI reasons. Humans decide.

That separation is the foundation of GridSense.

Rules provide speed and explainability.

Context prevents the system from confusing symptoms with causes.

AI handles difficult diagnostic reasoning.

Humans remain responsible for operational decisions.

👥 Team / Organization

<div align="center">

Built by AYU Systems

Powering intelligent operations for the renewable-energy era.

📧 hello@ayusystems.com🌐 www.ayusystems.com

</div>

📄 License

This project is released under the MIT License.

Synthetic telemetry and generic fault logic are used for demonstration. No proprietary employer data, confidential processes, or private operational data are included.

<div align="center">

⚡ GridSense

From alarm overload → contextual intelligence → actionable O&M

<a href="https://github.com/venkatanaveen2078909-rgb/gridsense-ai">
  <img src="https://img.shields.io/badge/View%20Repository-GitHub-black?style=for-the-badge&logo=github" alt="View Repository">
</a>

<br><br>

⭐ Star the repository if you find the project interesting.

</div>
