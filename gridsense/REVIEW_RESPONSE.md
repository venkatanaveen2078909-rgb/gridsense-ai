# GRIDSENSE — Response to Industry Review

A veteran solar-operations engineer reviewed GRIDSENSE and rated the concept
8.8/10 and MSME commercial potential 9.5/10, validating the architecture while
flagging that it was, in his words, "an AI-assisted alarm management system, not
yet a complete predictive asset management platform."

We took the review seriously and acted on it. This document maps every
substantive point to what we did: **shipped now**, **cited in roadmap**, or
**honestly deferred to Version 2**. Where we shipped, it is real, tested code —
not a slide.

---

## What we shipped in response (verified, tested)

### 1. Peer benchmarking — "every solar engineer compares assets"

The reviewer's strongest engineering point: an inverter at 390 kW while its
siblings produce ~540 kW is suspicious even though it clears every fixed
threshold. This is where silent 5–15% money leaks hide.

**Done.** A fleet-level detector now compares each inverter against the median
of its healthy peers and flags any asset at or below 85% of that median. On our
sample plant it catches INV-04 at 390 kW — 75% of the 522 kW peer median — while
correctly leaving the healthy siblings alone.

### 2. Performance Ratio (PR) — "one of the most important KPIs in solar"

He was surprised PR was absent. Fixed kW thresholds can't tell a cloudy day from
a fault; PR (actual ÷ expected-from-irradiance) can.

**Done.** The system now computes expected power from irradiance and nameplate
rating, and PR from that. A low-PR detector flags partial underperformance, and
PR is displayed on the work order. INV-04 surfaces at PR 0.73 — caught by both
PR and peer comparison, exactly the redundancy a real diagnosis wants.

### 3. Guard conditions — "reduces false positives enormously"

His biggest correctness concern: "bright sun + zero output = fault" is too naïve.
A real alert should first confirm the plant is running, the grid is up, and the
asset isn't in maintenance.

**Done.** A plant-context guard now suppresses any output-loss alert that the
plant state already explains. Verified: with the grid marked down, all 12
sample alarms correctly drop to zero; an asset under a maintenance ticket is
suppressed. We don't cry wolf when the loss is expected.

### 4. Probabilistic root cause — "rank probabilities rather than declaring a cause"

He noted an experienced engineer never concludes "inverter trip" from zero
output alone — they rank trip vs comms loss vs grid outage vs maintenance vs
stale SCADA value.

**Done.** The AI agent now returns a ranked cause list with probabilities, not a
single verdict. A tripped inverter now reads: 55% protection trip · 20% comms
loss · 15% grid outage · 10% maintenance mode. The prompt was rewritten to force
this ranked reasoning.

### 5. Diagnostic-first, cost-escalating recommendations

His point: crew dispatch must always be the expensive last option; confirm the
cause cheaply first (ping, check comms, check grid) before a truck roll.

**Done.** The agent is now instructed to produce diagnostic-first steps that
escalate cost. The tripped-inverter work order now reads: ping over Modbus →
attempt remote reset → check fiber/comms → *only then* dispatch crew.

### 6. Financial impact — "speak the language of CFOs"

Plant owners care about money, not JSON. He wanted ₹, not kWh.

**Done.** Every work order now converts lost energy to money at a configurable
tariff. The 520 kWh inverter loss now shows as ≈ ₹2,704; the partial INV-04 loss
as ≈ ₹686. Tariff and currency are configurable.

**All six are covered by the automated test suite (11 tests, all passing), and
run in the no-API-key `--scan` demo mode.**

---

## What we cite in the roadmap (signal maturity, don't over-build for a hackathon)

The reviewer rightly noted that industrial buyers look for standards and security
posture. Implementing these is a funded-deployment effort, not a hackathon task —
but naming them signals we know the terrain. Our roadmap and pitch now reference:

- **Data & interoperability standards** — IEC 61724 (PV performance monitoring),
  IEC 61850, Modbus TCP, DNP3, OPC UA, IEC 60870-5-104, SunSpec.
- **Security** — IEC 62443, role-based access, encrypted telemetry, read-only /
  zero-trust posture, and the audit log we already maintain.

We deliberately did not stub these in code. A hackathon prototype claiming full
IEC 62443 compliance would be less credible, not more.

---

## What we honestly defer to Version 2 (his roadmap, adopted)

The reviewer's Version 2 list is, frankly, an excellent product roadmap, and we
adopt it rather than pretend we've built it. These are genuine
funded-deployment items:

- Live SCADA / historian ingestion
- Weather-API normalisation (cloud cover, temperature, wind) to further cut
  false positives
- String- and combiner-level analysis (where 5–10% losses hide below the inverter)
- Degradation / trend analytics over time
- Unsupervised anomaly detection ("this inverter behaves unlike every other")
  for *unknown* faults, not just known rules
- Remaining-useful-life and failure-probability modelling
- Digital twin / expected-generation model
- CMMS integration (SAP PM, IBM Maximo, Fiix)
- Spare-parts and crew-scheduling optimisation
- Auto-generated RCA reports

Our honest-scope framing is unchanged: this is a working prototype of the triage
core, and the path from here to the platform above is exactly what a pilot funds.

---

## Net effect on the review's own scale

The reviewer said that with expected-vs-actual models, peer benchmarking,
probabilistic root-cause ranking, and financial impact, he would rate it
**9.5–9.8/10**. Four of those are now shipped and tested; weather normalisation,
degradation, and string-level analysis are the honest next tier.

We moved from "AI-assisted alarm management" meaningfully toward "AI-driven asset
performance management" — and we did it without faking the parts that genuinely
require a pilot. That distinction is the whole point, and we think it's what makes
the submission trustworthy.


---

**AYU Systems** · hello@ayusystems.com · www.ayusystems.com
