#!/usr/bin/env python3
"""
GRIDSENSE CLI — renewable-energy O&M triage agent.

Usage:
  # Preview what the rule engine flags (no API key needed):
  python run.py --scan samples/plant_telemetry.csv

  # Full run: detect + AI triage into work orders:
  python run.py --run samples/plant_telemetry.csv

Environment:
  export ANTHROPIC_API_KEY=sk-ant-...
  export GRIDSENSE_MODEL=claude-haiku-4-5   # optional (default)
"""
from __future__ import annotations
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.pipeline import process_file, scan_only  # noqa: E402
from app.agent import OMAgent  # noqa: E402
from app.schema import WorkItem  # noqa: E402

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
SEV_COLOR = {
    "Critical": "\033[91m", "High": "\033[93m", "Medium": "\033[96m",
    "Low": "\033[92m", "Informational": "\033[90m",
}


def render(w: WorkItem) -> str:
    c = SEV_COLOR.get(w.severity, "")
    # money line: kWh + rupees, the number owners care about
    impact = ""
    if w.est_energy_loss_kwh:
        impact = f"   {DIM}Est. loss:{RESET} {w.est_energy_loss_kwh} kWh"
        if w.est_revenue_loss:
            sym = "₹" if w.currency == "INR" else w.currency + " "
            impact += f" ≈ {sym}{w.est_revenue_loss:,.0f}"
    lines = [
        "",
        f"┌─ {w.work_id}  {DIM}{w.created_at}{RESET}",
        f"│ {c}{BOLD}{w.severity.upper()}{RESET}  ·  {w.asset_id} ({w.asset_type})  ·  "
        f"{BOLD}{w.action}{RESET}",
        f"│ {BOLD}{w.title}{RESET}",
    ]
    # performance context line (PR / peer median) when present
    perf = []
    if w.performance_ratio is not None and w.performance_ratio > 0.01:
        perf.append(f"PR {w.performance_ratio:.2f}")
    if w.peer_median_kw is not None:
        perf.append(f"peer median {w.peer_median_kw} kW")
    if perf:
        lines.append(f"│ {DIM}Performance:{RESET} " + "  ·  ".join(perf))
    # probable causes, ranked (not a single declared cause)
    if w.probable_causes:
        top = "  ·  ".join(f"{pc['probability']:.0%} {pc['cause']}"
                           for pc in w.probable_causes[:4])
        lines.append(f"│ {DIM}Probable causes:{RESET} {top}")
    else:
        lines.append(f"│ {DIM}Likely cause:{RESET} {w.likely_cause}")
    lines.append(
        f"│ {DIM}Confidence:{RESET} {w.confidence:.0%}   "
        f"{DIM}Approval:{RESET} {'REQUIRED' if w.needs_human_approval else 'not required'}"
        + impact
    )
    if w.recommended_steps:
        lines.append(f"│ {DIM}Steps:{RESET}")
        for i, step in enumerate(w.recommended_steps, 1):
            lines.append(f"│   {i}. {step}")
    lines.append(f"│ {DIM}Detector:{RESET} {w.source_rule}   "
                 f"{DIM}Rationale:{RESET} {w.reasoning}")
    lines.append("└" + "─" * 62)
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="GRIDSENSE O&M triage agent")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--scan", metavar="CSV", help="Rule-only preview (no AI/key).")
    g.add_argument("--run", metavar="CSV", help="Detect + AI triage into work orders.")
    args = ap.parse_args()

    if args.scan:
        anomalies = scan_only(args.scan)
        print(f"\nRule engine flagged {len(anomalies)} anomalies "
              f"(no AI, no key required):\n")
        for a in anomalies:
            print(f"  • [{a.rule}] {a.asset_id} ({a.asset_type}) — {a.detail}")
        print()
        return 0

    # --run
    try:
        agent = OMAgent()
    except Exception as e:
        print(f"\n[setup error] {e}\n", file=sys.stderr)
        return 2
    try:
        print(f"\nScanning {args.run} and triaging with {agent.model}…")
        items = process_file(args.run, agent=agent)
        if not items:
            print("No anomalies detected. All assets nominal.\n")
            return 0
        # Sort so the scariest work orders surface first.
        order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Informational": 4}
        for w in sorted(items, key=lambda x: order.get(x.severity, 9)):
            print(render(w))
        print(f"\n{DIM}{len(items)} work orders written to "
              f"{os.getenv('GRIDSENSE_LOG', 'gridsense_workorders.jsonl')}{RESET}\n")
    except Exception as e:
        print(f"\n[runtime error] {e}\n", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
