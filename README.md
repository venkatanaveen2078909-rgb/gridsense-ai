<div align="center">

# ⚡ GridSense

### AI-Powered Context-Aware SCADA Intelligence for Renewable Energy

*Detect the signal. Understand the context. Act on what matters.*

[![Project-GridSense](https://img.shields.io/badge/Project-GridSense-0A0A0A?style=for-the-badge&logo=github)](https://github.com/venkatanaveen2078909-rgb/gridsense-ai)
![License](https://img.shields.io/github/license/venkatanaveen2078909-rgb/gridsense-ai?style=for-the-badge)
![Stars](https://img.shields.io/github/stars/venkatanaveen2078909-rgb/gridsense-ai?style=for-the-badge)
![Last Commit](https://img.shields.io/github/last-commit/venkatanaveen2078909-rgb/gridsense-ai?style=for-the-badge)

<p>
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/MQTT-Telemetry-660066?style=flat-square&logo=mqtt&logoColor=white" alt="MQTT">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/AI-LLM%20Triage-8B5CF6?style=flat-square" alt="AI">
  <img src="https://img.shields.io/badge/SCADA-Intelligence-00A67E?style=flat-square" alt="SCADA">
</p>

[Why GridSense](#-why-gridsense) • [How It Works](#-how-it-works) • [Capabilities](#-key-capabilities) • [System Architecture](#-advanced-architecture) • [Quick Start](#-quick-start) • [Safety & Governance](#-safety--governance)

</div>

---

## 🚨 The Problem

Renewable-energy control rooms don't suffer from a lack of data. They suffer from a lack of **context**. 

A single grid event (e.g., a transmission line trip) cascades into hundreds of downstream alarms across solar inverters, transformers, and meters. This results in **alarm fatigue**, higher **Mean Time to Resolution (MTTR)**, and missed revenue.

```
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
```

Traditional SCADA tells operators **what** changed. **GridSense** tells them **why**.

---

## ⚡ Why GridSense?

GridSense is an AI-powered, context-aware SCADA intelligence layer that sits above existing telemetry infrastructure. It blends **deterministic detection**, **contextual reasoning**, and **automated safety isolation** into a single glass panel.

### The Core Design Principle
```
┌─────────────────────┐
│      Telemetry      │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Deterministic RPA  │  ← Fast, cheap, explainable rule engine
│   Rule Detectors    │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Context Correlation │  ← Plant state (Grid Down, Curtailed) + peer behaviour
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  OpenRouter AI L2   │  ← Google Gemini 2.5 Pro native JSON triage
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Auto-Shutdown / WO  │  ← Automated unit isolation & actionable O&M ticket
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│  Operator Override  │  ← Human-in-the-loop manual restart action
└─────────────────────┘
```

---

## ⚙️ Key Capabilities

* **🔍 Real-time Fault Detection:** Scans raw telemetry to identify abnormal equipment behaviour.
* **☀️ Performance Ratio Guardrails:** Separates weather-driven production loss from active mechanical or electrical faults.
* **📊 Peer Benchmarking:** Compares live assets against their immediate neighbors to catch subtle 5–15% underperformance.
* **🧠 Context-Aware Alarm Suppression:** Suppresses cascading alarms on solar arrays during grid-down, curtailed, or plant maintenance states.
* **🤖 AI Triage & Diagnostic Work-Orders:** Creates structured O&M tickets detailing likely causes, probability distributions, estimated revenue loss, and recommended steps.
* **🛡️ Automated Safety Isolation (Shutdown):** Automatically triggers shutdown overrides on assets experiencing critical telemetry threats to prevent physical/thermal damage.
* **👨‍🔧 Operator Restarts:** Keeps humans in the loop with graphical overrides to clear isolation states and resume operations.

---

## 🏗️ Advanced Architecture

The diagram below details the entire data flow: from simulation engines to ingestion pipelines, database schemas, background daemon OMAgents, and UI interaction hooks.

```mermaid
flowchart TD
    %% Telemetry Sources
    subgraph Data_Sources["1. Telemetry Generation Sources"]
        SCADA_Sim["SCADA Simulator\n(scada_simulator.py)"]
        MQTT_Sim["MQTT Simulator\n(mqtt_simulator.py)"]
        Mosquitto["Mosquitto Broker\n(mosquitto:1883)"]
        MQTT_Adapter["MQTT REST Adapter\n(app/mqtt_adapter.py)"]
    end

    %% Ingestion API
    subgraph Ingestion_API["2. Flask Backend API Ingest"]
        Ingest_Endpoint["POST /api/v2/ingest\n(web_app.py)"]
        Auth_Verify["Validate X-API-Key\n(API Security)"]
    end

    %% Database Layer
    subgraph Storage["3. PostgreSQL Storage"]
        DB_Telemetry["telemetry table\n(processed = FALSE)"]
        DB_Incidents["incidents table\n(Active/Resolved)"]
        DB_WorkOrders["work_orders table\n(AI Triage Results)"]
        DB_PlantState["plant_state table\n(shut_down_assets JSONB)"]
    end

    %% Background Daemon
    subgraph Daemon["4. Background Monitor Thread (_monitor_loop)"]
        Fetch_Unprocessed["Fetch unprocessed telemetry"]
        Metric_Calc["Calculate Peer Medians\n& Performance Ratios"]
        Rule_Engine["Deterministic Rule Engine\n(app/detectors.py)"]
        Update_Incidents["Insert New Incidents\n/ Resolve Stale Incidents"]
        Mark_Processed["Update telemetry\n(processed = TRUE)"]
        Triage_Check["AI Cooldown Check\n(Has WO been created in last 15m?)"]
    end

    %% AI Triage
    subgraph AI_Triage["5. AI Triage Reasoning Pipeline"]
        OMAgent["OMAgent factory\n(app/agent.py)"]
        OpenRouter["OpenRouterAgent\n(Gemini 2.5 Pro via HTTP)"]
        JSON_Parse["Robust Regex Fallback\nJSON Parser"]
        WO_Build["Assemble WorkItem\n(app/agent.py:build_workitem)"]
        Save_WO["Insert into work_orders"]
    end

    %% Safety Shutdown
    subgraph Safety_Loop["6. AI Safety Shutdown Isolation"]
        Severity_Check{"Is Triage Severity\n'Critical'?"}
        Update_Shutdown_List["Add asset_id to\nshut_down_assets list"]
    end

    %% Simulator Sync
    subgraph Sim_Sync["7. SCADA Simulator Feedback Loop"]
        Poll_Ctx["GET /api/v2/simulator-context\n(Every 6s)"]
        Forced_Zero{"Is Asset ID in\nshut_down_assets?"}
        Override_Metrics["Force power_kw & current_a\nto 0.0 (Isolated)"]
        Jitter_Metrics["Apply random jitter\n(Normal operation)"]
    end

    %% UI Dashboard
    subgraph UI_Layer["8. Dashboard Frontend UI (dashboard.html)"]
        Poll_Fleet["Poll GET /api/live/fleet\n(Every few seconds)"]
        Fetch_State["GET /api/context\n(JWT Authenticated)"]
        Suppression_Logic{"Is Grid Down,\nCurtailed, or Asset\nShut Down?"}
        Suppress_UI["Suppress active anomalies\nSet status to 'shutdown'"]
        Render_UI["Render Slate-grey Dot\n& Warning Cards with\n'Restart' Buttons"]
        Operator_Click["Operator clicks 'Restart'\nPOST /api/context"]
    end

    %% Data Flow Connections
    SCADA_Sim -->|HTTP POST JSON| Ingest_Endpoint
    MQTT_Sim -->|Publish MQTT| Mosquitto
    Mosquitto -->|Subscribe| MQTT_Adapter
    MQTT_Adapter -->|HTTP POST JSON| Ingest_Endpoint
    
    Ingest_Endpoint --> Auth_Verify
    Auth_Verify -->|Insert records| DB_Telemetry

    Daemon -->|Poll every 3s| Fetch_Unprocessed
    Fetch_Unprocessed --> DB_Telemetry
    Fetch_Unprocessed --> Metric_Calc
    Metric_Calc --> Rule_Engine
    Rule_Engine --> Update_Incidents
    Update_Incidents --> DB_Incidents
    Rule_Engine --> Mark_Processed
    Mark_Processed --> DB_Telemetry
    
    Update_Incidents --> Triage_Check
    Triage_Check -->|Cooldown Passed| OMAgent
    OMAgent --> OpenRouter
    OpenRouter -->|Returns JSON Text + Reasoning| JSON_Parse
    JSON_Parse --> WO_Build
    WO_Build --> Save_WO
    Save_WO --> DB_WorkOrders
    WO_Build --> Severity_Check

    Severity_Check -->|Yes| Update_Shutdown_List
    Update_Shutdown_List --> DB_PlantState

    SCADA_Sim -->|Polls| Poll_Ctx
    Poll_Ctx --> DB_PlantState
    Poll_Ctx --> Forced_Zero
    Forced_Zero -->|Yes| Override_Metrics
    Forced_Zero -->|No| Jitter_Metrics
    Jitter_Metrics --> SCADA_Sim
    Override_Metrics --> SCADA_Sim

    UI_Layer --> Poll_Fleet
    Poll_Fleet --> DB_Telemetry
    UI_Layer --> Fetch_State
    Fetch_State --> DB_PlantState
    Fetch_State --> Suppression_Logic
    Suppression_Logic --> Suppress_UI
    Suppress_UI --> Render_UI
    Operator_Click -->|Clears asset from list| DB_PlantState
```

---

## 🚀 Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/venkatanaveen2078909-rgb/gridsense-ai.git
cd gridsense-ai

# Initialize virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration (`.env`)
Create a `.env` file from the provided example:
```bash
cp .env.example .env
```
Configure your credentials:
```env
# Database Configuration (Docker Compose handles default port 5432)
POSTGRES_DB=gridsense_db
POSTGRES_USER=gridsense
POSTGRES_PASSWORD=password123
POSTGRES_HOST=db

# OpenRouter Configuration
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=google/gemini-2.5-pro
```

### 3. Running Locally with Docker Compose
To launch the full suite (PostgreSQL database, Mosquitto MQTT Broker, Flask Web backend, and simulators):
```bash
docker compose up -d
```
Once initialized:
- Access the web dashboard at: **[http://localhost:5000](http://localhost:5000)**
- Default Operator login credentials:
  - **AeroWind Corp:** `admin@aerowind.com` | `password123`
  - **Solaris Energy:** `admin@solaris.com` | `password123`

---

## 🧪 Demo Fault Matrix

| Asset Type | Active Anomaly | AI Triage Outcome | Context Logic | Safety Shutdown Trigger |
| :--- | :--- | :--- | :--- | :--- |
| **Solar Inverter** | Zero Output under high light | High Severity (RemoteReset) | Suppressed if grid goes down | No (Warning banner only) |
| **Solar Inverter** | Internal Overtemperature | Critical Severity (Shutdown) | Monitored individually | **Yes (Forced to 0.0 kW)** |
| **Wind Turbine** | Vibration exceeding threshold | Critical Severity (Shutdown) | High wind limits checked | **Yes (Forced to 0.0 kW)** |
| **Transformer** | Oil Temperature Alarm | Critical Severity (Shutdown) | Load percentage checked | **Yes (Isolated)** |
| **Revenue Meter** | Communication Loss | High Severity (RaiseTicket) | Evaluates adjacent devices | No (Warning banner only) |

---

## 🛡️ Safety & Governance

GridSense separates **Detection** from **Reasoning** and **Execution**:
1. **Deterministic Screening:** Standard rule engines handle the high-volume data stream. AI is only engaged when an active incident is flagged.
2. **Context-Aware Suppression:** Ensures grid disturbances don't flood the operator or AI agents with duplicate incident notifications.
3. **Safety Isolation Override:** Critical physical safety risks are automatically isolated to prevent equipment damage, while retaining **Human-in-the-loop manual override buttons** so technicians can safely override and restart assets.

---

*Powering intelligent operations for the renewable-energy era.*
