"""
Module các hàng rào an toàn y tế (Clinical Guardrails) cho Aftercare-AI.
"""
from backend.app.guardrails.evidence_gate import (
    EvidenceGate,
    EvidenceGateVerdict,
    get_chunk_score,
)
from backend.app.guardrails.input_guard import InputPolicyGuard, PolicyMatchResult
from backend.app.guardrails.output_guard import (
    OutputGuardResult,
    OutputPolicyGuard,
    get_default_output_guard,
)
from backend.app.guardrails.pii_redactor import PIIRedactor, default_pii_redactor
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
    "EvidenceGate",
    "EvidenceGateVerdict",
    "InputPolicyGuard",
    "NO_EVIDENCE_MESSAGE",
    "OutputGuardResult",
    "OutputPolicyGuard",
    "PIIRedactor",
    "PolicyMatchResult",
    "SAFE_FALLBACK_MESSAGE",
    "build_emergency_response",
    "build_safe_refusal_response",
    "build_yellow_zone_response",
    "default_pii_redactor",
    "get_chunk_score",
    "get_default_output_guard",
]

