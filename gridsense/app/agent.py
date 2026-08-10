"""
The reasoning agent.

Takes a rule-detected Anomaly and uses an AI model (Claude or Groq) to:
  1. Diagnose the likely cause (from the metrics + asset type)
  2. Assign a severity band for O&M prioritisation
  3. Recommend an action category (dispatch / remote reset / schedule / monitor)
  4. Draft concrete, ordered steps for the field crew
  5. Estimate energy loss where the data supports it

Supports two backends (auto-selected based on which API key is set):
  - Groq  (GROQ_API_KEY)      — free, fast, uses llama-3.3-70b-versatile
  - Claude (ANTHROPIC_API_KEY) — original, uses claude-haiku-4-5

Structured (forced tool-use / function-calling) output so the result is
guaranteed-shaped data a work-order system can consume.
"""
from __future__ import annotations
import json
from .config import (
    ANTHROPIC_MODEL, ANTHROPIC_API_KEY, MAX_TOKENS,
    GROQ_API_KEY, GROQ_MODEL,
    OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL,
    SEVERITIES, ACTIONS,
)
from .schema import Anomaly, WorkItem
from .logging_config import get_logger
from .retry import with_retry

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Shared tool / function schema (used by both Claude and Groq)
# ---------------------------------------------------------------------------
TRIAGE_TOOL = {
    "name": "record_workitem",
    "description": (
        "Record the diagnosis and recommended response for a detected asset "
        "anomaly at a renewable energy plant. Call exactly once."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "severity": {"type": "string", "enum": SEVERITIES,
                         "description": "Operational severity for prioritisation."},
            "action": {"type": "string", "enum": ACTIONS,
                       "description": "Recommended response category."},
            "confidence": {"type": "number", "description": "0.0-1.0 confidence in the diagnosis."},
            "title": {"type": "string", "description": "One-line summary for the O&M queue."},
            "likely_cause": {"type": "string", "description": "Single most probable root cause."},
            "probable_causes": {
                "type": "array",
                "description": (
                    "Ranked candidate causes with probabilities summing to ~1.0. "
                    "Provide 3-5 entries."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "cause": {"type": "string"},
                        "probability": {"type": "number"},
                    },
                    "required": ["cause", "probability"],
                },
            },
            "recommended_steps": {
                "type": "array", "items": {"type": "string"},
                "description": "Ordered, concrete steps for the crew or operator.",
            },
            "est_energy_loss_kwh": {
                "type": ["number", "null"],
                "description": "Rough energy loss estimate if inferable, else null.",
            },
            "reasoning": {"type": "string", "description": "Two-sentence rationale for the audit log."},
        },
        "required": ["severity", "action", "confidence", "title",
                     "likely_cause", "probable_causes", "recommended_steps", "reasoning"],
    },
}

# Groq / OpenAI use a slightly different function schema format
GROQ_FUNCTION = {
    "type": "function",
    "function": {
        "name": TRIAGE_TOOL["name"],
        "description": TRIAGE_TOOL["description"],
        "parameters": TRIAGE_TOOL["input_schema"],
    },
}

SYSTEM_PROMPT = (
    "You are the triage agent for the operations & maintenance (O&M) team of a "
    "renewable energy plant (solar and wind). You receive a single anomaly that "
    "a rule engine detected from asset telemetry. Diagnose it, rate severity, "
    "recommend one response action, and draft concrete steps.\n\n"
    "Guidance:\n"
    "- RANK causes, don't declare one. From limited telemetry, a zero-output "
    "inverter could be a protection trip, a comms loss, a grid outage, "
    "maintenance mode, or a stale SCADA value. Return probable_causes as a "
    "ranked list with probabilities summing to ~1.0, and set likely_cause to "
    "the top one.\n"
    "- Steps should be DIAGNOSTIC-FIRST and escalate cost. Confirm the cause "
    "cheaply before spending money: check comms/ping, verify grid and neighbour "
    "inverters, rule out maintenance — and only THEN dispatch a crew.\n"
    "- Prefer the cheapest safe action first (RemoteReset over DispatchTechnician).\n"
    "- Reserve 'Critical' for safety risks or large active generation loss.\n"
    "- Only estimate energy loss when the metrics support it; otherwise null.\n"
    "- Base your diagnosis only on the metrics provided. Do not invent readings.\n"
    "- You recommend; a human approves before any crew is dispatched.\n"
    "- Always call the record_workitem tool exactly once."
)

def _sanitize(text: str) -> str:
    """Robust sanitization to prevent prompt injection and PII leakage."""
    import re
    if not isinstance(text, str):
        return str(text)
    
    # 1. Remove markdown blocks and template execution syntax
    clean = text.replace("```", "").replace("{{", "").replace("}}", "")
    
    # 2. Strip common prompt injection keywords (case-insensitive)
    injection_patterns = [
        r"(?i)\bignore\s+(all\s+)?(previous\s+)?instructions\b",
        r"(?i)\b(system|user|assistant)\s*prompt\b",
        r"(?i)\bforget\s+everything\b",
        r"(?i)\b(bypass|override|jailbreak)\b",
        r"(?i)\byou\s+are\s+now\b",
        r"(?i)\bdrop\s+table\b",
        r"(?i)<\|.*?\|>" # Common LLM special tokens
    ]
    
    for pattern in injection_patterns:
        clean = re.sub(pattern, "[REDACTED]", clean)
        
    return clean.strip()

def _build_user_prompt(a: Anomaly) -> str:
    metrics_lines = "\n".join(f"  {k}: {v}" for k, v in a.metrics.items())
    return (
        f"Asset: {_sanitize(a.asset_id)} ({_sanitize(a.asset_type)})\n"
        f"Time: {_sanitize(a.timestamp)}\n"
        f"Detector: {_sanitize(a.rule)}\n"
        f"Deviation: {_sanitize(a.detail)}\n"
        f"Metrics snapshot:\n{metrics_lines}"
    )


# ---------------------------------------------------------------------------
# Groq backend
# ---------------------------------------------------------------------------
class GroqAgent:
    """Uses Groq's free LLM API (OpenAI-compatible) for triage."""

    def __init__(self, model: str = GROQ_MODEL):
        from groq import Groq
        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Export it before running:\n"
                "  $env:GROQ_API_KEY='gsk_...'"
            )
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = model
        log.info("AI backend initialised", extra={"backend": "groq", "model": model})

    @with_retry(max_attempts=3, base_delay=2.0)
    def triage(self, a: Anomaly) -> dict:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(a)},
            ],
            tools=[GROQ_FUNCTION],
            tool_choice={"type": "function", "function": {"name": "record_workitem"}},
            max_tokens=MAX_TOKENS,
            timeout=30.0,
        )
        for choice in resp.choices:
            msg = choice.message
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.function.name == "record_workitem":
                        return json.loads(tc.function.arguments)
        raise RuntimeError("Groq agent did not return a work-item tool call.")


# ---------------------------------------------------------------------------
# OpenRouter backend (OpenAI-compatible, supports many models)
# ---------------------------------------------------------------------------
class OpenRouterAgent:
    """Uses OpenRouter's OpenAI-compatible API for triage."""

    def __init__(self, model: str = OPENROUTER_MODEL):
        from openai import OpenAI
        if not OPENROUTER_API_KEY:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Export it before running:\n"
                "  $env:OPENROUTER_API_KEY='sk-or-...'"
            )
        self.client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
        )
        self.model = model
        log.info("AI backend initialised", extra={"backend": "openrouter", "model": model})

    @with_retry(max_attempts=3, base_delay=2.0)
    def triage(self, a: Anomaly) -> dict:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(a)},
            ],
            tools=[GROQ_FUNCTION],
            tool_choice={"type": "function", "function": {"name": "record_workitem"}},
            max_tokens=MAX_TOKENS,
            timeout=30.0,
        )
        for choice in resp.choices:
            msg = choice.message
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc.function.name == "record_workitem":
                        return json.loads(tc.function.arguments)
        raise RuntimeError("OpenRouter agent did not return a work-item tool call.")


# ---------------------------------------------------------------------------
# Claude backend (original)
# ---------------------------------------------------------------------------
class ClaudeAgent:
    """Uses Anthropic Claude API for triage."""

    def __init__(self, model: str = ANTHROPIC_MODEL):
        from anthropic import Anthropic
        if not ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Export it before running:\n"
                "  export ANTHROPIC_API_KEY=sk-ant-..."
            )
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = model
        log.info("AI backend initialised", extra={"backend": "claude", "model": model})

    @with_retry(max_attempts=3, base_delay=2.0)
    def triage(self, a: Anomaly) -> dict:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=[TRIAGE_TOOL],
            tool_choice={"type": "tool", "name": "record_workitem"},
            messages=[{
                "role": "user",
                "content": _build_user_prompt(a),
            }],
            timeout=30.0,
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == "record_workitem":
                return block.input
        raise RuntimeError("Claude agent did not return a work-item tool call.")


# ---------------------------------------------------------------------------
# Auto-select backend + public alias
# ---------------------------------------------------------------------------
def OMAgent(model: str = None):
    """
    Factory function — returns the best available AI backend.
    Priority: OpenRouter > Groq > Claude
    """
    if OPENROUTER_API_KEY:
        return OpenRouterAgent(model or OPENROUTER_MODEL)
    if GROQ_API_KEY:
        return GroqAgent(model or GROQ_MODEL)
    if ANTHROPIC_API_KEY:
        return ClaudeAgent(model or ANTHROPIC_MODEL)
    raise RuntimeError(
        "No AI API key found.\n"
        "Set OPENROUTER_API_KEY (recommended), GROQ_API_KEY (free), or ANTHROPIC_API_KEY and re-run.\n"
        "  OpenRouter: $env:OPENROUTER_API_KEY='sk-or-...'\n"
        "  Groq:       $env:GROQ_API_KEY='gsk_...'\n"
        "  Claude:     $env:ANTHROPIC_API_KEY='sk-ant-...'"
    )


# ---------------------------------------------------------------------------
# Shared helpers (unchanged)
# ---------------------------------------------------------------------------
def _approval_policy(data: dict) -> bool:
    """
    Human approval required by default. Only low-risk, high-confidence
    'MonitorOnly' or 'RaiseTicketOnly' outcomes may skip approval.
    """
    if data.get("action") in ("MonitorOnly", "RaiseTicketOnly"):
        return float(data.get("confidence", 0)) < 0.85
    return True


def _normalise_causes(raw) -> list:
    """Clean the model's probable_causes into a sorted, normalised list."""
    out = []
    for c in (raw or []):
        try:
            out.append({"cause": str(c["cause"]),
                        "probability": max(0.0, min(1.0, float(c["probability"])))})
        except (KeyError, TypeError, ValueError):
            continue
    total = sum(c["probability"] for c in out)
    if total > 0:
        for c in out:
            c["probability"] = round(c["probability"] / total, 2)
    return sorted(out, key=lambda c: c["probability"], reverse=True)


def build_workitem(a: Anomaly, agent) -> WorkItem:
    from .config import TARIFF_PER_KWH, CURRENCY
    data = agent.triage(a)

    loss_kwh = data.get("est_energy_loss_kwh")
    revenue_loss = round(loss_kwh * TARIFF_PER_KWH, 0) if loss_kwh else None

    peer_median = a.metrics.get("_peer_median_kw")

    return WorkItem(
        work_id=WorkItem.new_id(),
        created_at=WorkItem.now_iso(),
        asset_id=a.asset_id,
        asset_type=a.asset_type,
        severity=data["severity"],
        action=data["action"],
        confidence=float(data["confidence"]),
        title=data["title"],
        likely_cause=data["likely_cause"],
        probable_causes=_normalise_causes(data.get("probable_causes")),
        recommended_steps=list(data.get("recommended_steps", [])),
        est_energy_loss_kwh=loss_kwh,
        performance_ratio=a.metrics.get("_performance_ratio"),
        peer_median_kw=peer_median,
        est_revenue_loss=revenue_loss,
        currency=CURRENCY,
        needs_human_approval=_approval_policy(data),
        reasoning=data.get("reasoning", ""),
        source_rule=a.rule,
    )
