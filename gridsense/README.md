# GRIDSENSE — Renewable-Energy O&M Triage Agent

*AYU Systems · hello@ayusystems.com · www.ayusystems.com*

An AI agent that watches renewable-plant telemetry, catches faults, diagnoses
them, and drafts the maintenance response — with a human approving before
anything is dispatched. Built for the **Power / Renewables / Energy Efficiency**
track of an MSME hackathon.

It demonstrates the pattern judges look for: **deterministic RPA + an AI agent**.
Cheap, explainable rules sift the telemetry; the AI agent reasons about the
interesting deviations and writes the work order. A human stays in the loop.

Everything here is original and generic — synthetic telemetry, standard fault
logic, no proprietary data or processes from any employer.

## What it does

```
telemetry CSV ──► rule detectors (RPA) ──► AI agent triage ──► prioritised work orders ──► audit log
```

For each detected anomaly the agent produces a work order with:
- **severity** (Critical → Informational) and an **action** (remote reset,
  dispatch crew, schedule maintenance, monitor, ticket-only)
- a **likely cause** diagnosis and **ordered crew steps**
- an **energy-loss estimate** where the data supports one
- **needs_human_approval** — the agent proposes; a human dispatches
- a **rationale**, logged for every decision

It handles solar inverters, solar strings, wind turbines, transformers,
trackers, and meters out of the box. Detection goes beyond fixed thresholds:

- **Performance Ratio (PR)** — expected vs. actual power from irradiance and
  rating, so it distinguishes a cloudy day from a real fault.
- **Peer benchmarking** — compares each inverter against the median of its
  healthy siblings, catching silent 5–15% underperformance no threshold would.
- **Guard conditions** — suppresses alerts the plant state already explains
  (grid down, curtailment, open maintenance ticket), cutting false positives.
- **Probabilistic root cause** — the AI ranks candidate causes with
  probabilities (55% trip · 20% comms · 15% grid…) rather than declaring one.
- **Financial impact** — every work order shows lost energy in kWh *and* money
  (₹, configurable tariff), the number owners actually act on.

See `REVIEW_RESPONSE.md` for how these map to an industry engineer's review.

## Why it fits the sector and the MSME angle

- **Sector fit:** solar + wind generation, electrical assets (transformers),
  and energy efficiency (catching generation loss fast) — squarely inside
  "Power, Renewables, Electricals, Energy Efficiency and any related sub-sector."
- **MSME angle:** small solar/wind operators and C&I rooftop owners can't staff
  a 24/7 monitoring desk. This agent gives a lean team the triage layer a large
  utility would have — cheap rules for the bulk, AI only for the judgement calls.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

The detector layer and CSV ingest use only the standard library — no heavy ML deps.

## Run

```bash
# See what the rule engine flags — NO API key needed (great for a live demo):
python run.py --scan samples/plant_telemetry.csv

# Full run: detect + AI triage into prioritised work orders:
python run.py --run samples/plant_telemetry.csv
```

The sample telemetry seeds one of every fault type — a tripped inverter in full
sun, an over-temp inverter, a dead solar string, an underperforming turbine, a
hot gearbox, high nacelle vibration, an overloaded transformer, a stuck tracker,
and a meter comms loss — plus healthy assets that correctly raise nothing.

## Verify without an API key

```bash
python tests/test_offline.py
```

Detectors are pure functions and fully tested; the agent is mocked so the
work-item building and approval policy are verified with no network call.

## Safety / governance (built in)

- **Human-in-the-loop by default.** Anything that touches an asset or sends a
  crew requires approval. Only high-confidence "monitor" / "ticket-only"
  outcomes can skip it.
- **Cheapest safe action first.** A tripped inverter gets a remote-reset
  recommendation before a truck roll.
- **No invented readings.** The agent diagnoses only from the metrics given.
- **Full audit trail.** Every work order (with rationale) is appended to
  `gridsense_workorders.jsonl`.

## Architecture

| Layer | File | Real-world equivalent |
|---|---|---|
| Telemetry ingest | `app/pipeline.py` | SCADA / IoT historian feed |
| Anomaly detection (RPA) | `app/detectors.py` | Rule engine / alarm system |
| Reasoning agent (AI) | `app/agent.py` | Claude, forced structured output |
| Work-order builder + log | `app/pipeline.py` | CMMS / work-order system |
| Human approval | policy in `app/agent.py` | O&M supervisor sign-off |

## Extending it

- **New asset or fault:** add a rule in `app/detectors.py` returning `Anomaly`.
- **Live data:** replace the CSV reader with your SCADA/historian poll; the rest
  is unchanged.
- **Harder diagnoses:** `export GRIDSENSE_MODEL=claude-sonnet-4-6`.
- **Real work-order system:** replace `_log` with an API call to your CMMS.

## What this is not

A demonstrable prototype of the triage core, not a finished plant SCADA system.
It runs on sample/synthetic telemetry and outputs work orders; wiring it to a
live historian and a real CMMS is the build-out a hackathon win would fund.
```


---

**AYU Systems** · hello@ayusystems.com · www.ayusystems.com
