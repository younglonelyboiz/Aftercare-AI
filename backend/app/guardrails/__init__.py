"""
Module các hàng rào an toàn y tế (Clinical Guardrails) cho Aftercare-AI.
"""
from backend.app.guardrails.templates_vi import (
    DEFAULT_RED_ACTION,
    DEFAULT_YELLOW_ACTION,
    EMPTY_INPUT_MESSAGE,
    NO_EVIDENCE_MESSAGE,
    SAFE_FALLBACK_MESSAGE,
    build_emergency_response,
    build_safe_refusal_response,
    build_yellow_zone_response,
)

__all__ = [
    "DEFAULT_RED_ACTION",
    "DEFAULT_YELLOW_ACTION",
    "EMPTY_INPUT_MESSAGE",
    "NO_EVIDENCE_MESSAGE",
    "SAFE_FALLBACK_MESSAGE",
    "build_emergency_response",
    "build_safe_refusal_response",
    "build_yellow_zone_response",
]

