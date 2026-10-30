import json
import re

import httpx
from django.conf import settings

from .models import CheckLog

SYSTEM_PROMPT = """You are a site reliability assistant. You receive recent
health-check data for one monitored website that is currently failing.
Analyze ONLY the data provided. Do not invent facts. If the data is
insufficient to determine a cause, say so and use a low confidence.
Respond with a single JSON object and nothing else, with keys:
"summary" (string, 2 sentences max),
"possible_cause" (string, under 200 characters),
"confidence_score" (number between 0 and 1),
"recommended_actions" (list of up to 4 short strings)."""

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class AIAnalysisError(Exception):
    """Raised when analysis fails. `retryable` says whether trying again can help."""

    def __init__(self, message, retryable=True):
        super().__init__(message)
        self.retryable = retryable


def build_context(check_log, limit=30):
    site = check_log.site
    recent = (CheckLog.objects
              .filter(site=site, timestamp__lte=check_log.timestamp)
              .order_by("-timestamp")[:limit])
    return {
        "site_name": site.name,
        "site_url": site.url,
        "expected_status_code": site.expected_status_code,
        "timeout_seconds": site.timeout_seconds,
        "recent_checks_newest_first": [{
            "time": l.timestamp.isoformat(),
            "ok": l.is_successful,
            "status_code": l.status_code,
            "latency_ms": l.response_time_ms,
            "error": (l.error_message or "")[:200],
        } for l in recent],
    }


def _extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise AIAnalysisError("Model did not return JSON", retryable=True)
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            raise AIAnalysisError("Model returned malformed JSON", retryable=True)


def analyze(check_log):
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{
            "role": "user",
            "parts": [{"text": json.dumps(build_context(check_log))}],
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 800,
            "temperature": 0.2,
        },
    }

    try:
        resp = httpx.post(
            API_URL.format(model=settings.AI_MODEL),
            json=payload,
            headers={"x-goog-api-key": settings.GEMINI_API_KEY},
            timeout=30.0,
        )
    except httpx.RequestError as exc:
        raise AIAnalysisError(f"Network error calling Gemini: {type(exc).__name__}")

    if resp.status_code != 200:
        # retry only rate limits and server errors; 400/403/404 = bad key or model name
        retryable = resp.status_code == 429 or resp.status_code >= 500
        raise AIAnalysisError(f"Gemini returned HTTP {resp.status_code}", retryable=retryable)

    try:
        candidate = resp.json()["candidates"][0]
        text = candidate["content"]["parts"][0]["text"]
    except (KeyError, IndexError, ValueError):
        raise AIAnalysisError("Gemini response had no usable text", retryable=True)

    data = _extract_json(text)
    if not isinstance(data, dict):
        raise AIAnalysisError("Model JSON was not an object", retryable=True)

    try:
        score = max(0.0, min(1.0, float(data.get("confidence_score", 0))))
    except (TypeError, ValueError):
        score = 0.0

    actions = data.get("recommended_actions") or []
    if isinstance(actions, str):
        actions = [actions]

    return {
        "summary": str(data.get("summary", "")).strip()[:2000] or "No summary returned.",
        "possible_cause": str(data.get("possible_cause", "Unknown")).strip()[:255],
        "confidence_score": score,
        "recommended_action": "\n".join(f"- {a}" for a in actions[:4]) or "Inspect the target site.",
    }