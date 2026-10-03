from typing import Any, Dict, List, TypedDict


class SahaaraState(TypedDict, total=False):
    # inputs
    transcript: str
    user_text: str
    language_override: str
    documents: List[Dict[str, Any]]
    force_answer: bool
    clar_rounds: int
    # structured understanding
    language: str
    age_group: str
    symptoms: List[str]
    duration: str
    severity: str
    measurements: Dict[str, float]
    measurements_raw: Dict[str, Any]
    medical_history: List[str]
    medications: List[str]
    user_hypotheses: List[str]
    scenario_ids: List[str]
    critical_missing: List[str]
    emergency_suspected: bool
    emergency_reason: str
    needs_evaluation: bool
    evaluation_reason: str
    # reasoning
    possible_contexts: List[str]
    flags: List[Dict[str, str]]
    red_flags: List[str]
    risk_level: str  # green | yellow | red
    retrieved_evidence: List[Dict[str, str]]
    # outputs
    questions: List[str]
    bundle_en: Dict[str, Any]
    bundle_final: Dict[str, Any]
    referral: Dict[str, Any]
    attempts: int
    audit: Dict[str, Any]
    case_summary: str
    final_response: str
    response_type: str  # clarify | emergency | guidance | fallback
    trace: List[Dict[str, str]]
