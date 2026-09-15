import re
from typing import Final

from pydantic import BaseModel, Field


class SecurityCheckResult(BaseModel):
    allowed: bool
    is_prompt_injection: bool
    is_travel_related: bool
    reason: str = Field(max_length=240)


_INJECTION_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\b(ignore|disregard|forget|bypass)\b.{0,80}\b(previous|prior|system|hidden|all)\b.{0,80}\b(instruction|rule|prompt)s?\b", re.I | re.S),
    re.compile(r"\b(reveal|show|print|expose|repeat| disclose)\b.{0,80}\b(system prompt|hidden instructions?|internal prompt|api keys?|environment variables?|secrets?|credentials?|langgraph state|tool definitions?)\b", re.I | re.S),
    re.compile(r"\b(you are now|from now on|act as|pretend you are|become)\b.{0,80}\b(unrestricted|system administrator|coding assistant|different ai|another assistant)\b", re.I | re.S),
    re.compile(r"\b(call|run|execute|use)\b.{0,50}\b(every|all|any)\b.{0,50}\b(tool|database|internal)\b", re.I | re.S),
    re.compile(r"\b(follow|obey|execute)\b.{0,80}\b(instructions?|commands?)\b.{0,80}\b(document|website|text|content|quote)\b", re.I | re.S),
)

_INTERNAL_REQUEST: Final[re.Pattern[str]] = re.compile(
    r"\b(what is|what are|show|tell me|reveal|print|repeat|disclose|expose)\b.{0,60}\b(your )?(system prompt|hidden instructions?|api key|api keys|environment variables?|credentials?|secrets?|langgraph state|internal tools?|tool definitions?)\b",
    re.I,
)
_UNRELATED_REQUEST: Final[re.Pattern[str]] = re.compile(
    r"\b(write|create|generate|solve|help with|build)\b.{0,80}\b(malware|ransomware|phishing|python program|python game|political speech|campaign speech|university assignment|hack (a|the) website)\b",
    re.I | re.S,
)
_TRAVEL_CONTEXT: Final[re.Pattern[str]] = re.compile(
    r"\b(travel|trip|destination|itinerary|restaurant|halal|food|visa|passport|customs|policy|policies|etiquette|weather|currency|budget|expense|hotel|flight|airport|attraction|places? to visit|packing|transport|tour|tourist|luggage|booking)\b",
    re.I,
)


def _looks_like_injection(message: str) -> bool:
    if _INTERNAL_REQUEST.search(message):
        return True
    if any(pattern.search(message) for pattern in _INJECTION_PATTERNS):
        return True
    has_quoted_content = bool(re.search(r"[\"'`]", message))
    has_override = bool(re.search(r"\b(ignore|reveal|follow|obey|override)\b", message, re.I))
    return has_quoted_content and has_override and bool(_INTERNAL_REQUEST.search(message))


def check_user_message(message: str) -> SecurityCheckResult:
    """Classify one untrusted message before it reaches the travel graph.

    This is intentionally conservative: conversational travel corrections such as
    "forget Dubai" or "ignore the previous restaurant list" remain allowed.
    """
    normalized = " ".join(message.split())
    if _looks_like_injection(normalized):
        return SecurityCheckResult(
            allowed=False,
            is_prompt_injection=True,
            is_travel_related=False,
            reason="instruction override or internal-information request",
        )
    if _UNRELATED_REQUEST.search(normalized) or re.search(r"\b(write|generate|solve|hack)\b", normalized, re.I) and not _TRAVEL_CONTEXT.search(normalized):
        return SecurityCheckResult(
            allowed=False,
            is_prompt_injection=False,
            is_travel_related=False,
            reason="request is outside travel assistance",
        )
    return SecurityCheckResult(
        allowed=True,
        is_prompt_injection=False,
        is_travel_related=bool(_TRAVEL_CONTEXT.search(normalized)),
        reason="allowed travel conversation",
    )