"""End-to-end graph tests with a mocked LLM (no API key needed)."""
import os
os.environ["SAHAARA_EMBEDDINGS"] = "off"

from sahaara import llm
from sahaara.graph import build_graph

SUPPORT_OK = {"understood": "You have had dizziness for a day.", "relevant": "These symptoms can be associated with several causes.",
              "to_check": ["BP", "glucose"], "do_now": ["Sit down", "Sip ORS"], "warning_signs": ["Fainting", "Chest pain", "Confusion"],
              "follow_up": "See a doctor if it continues."}


def fake(understand, clarify=None, support=None, audit_pass=True):
    def _chat(system, user, **kw):
        if "Patient Understanding" in system:
            return understand
        if "Clarification Agent" in system:
            return {"questions": clarify or []}
        if "Early Support" in system:
            return support or SUPPORT_OK
        if "Health Literacy" in system:
            import json
            return json.loads(user)
        if "Safety Auditor" in system:
            return {"pass": audit_pass, "issues": [] if audit_pass else ["bad"]}
        return {}
    return _chat


BASE = {"language": "roman_ur", "age_group": "adult", "symptoms": ["dizziness"], "duration": "1 day",
        "scenario_ids": ["dizziness"], "critical_missing": [], "emergency_suspected": False, "needs_evaluation": False}


def run(text, **kw):
    return build_graph().invoke({"transcript": "User: " + text, "user_text": text, "clar_rounds": 0, **kw})


def test_emergency_skips_llm_guidance(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", fake(BASE))
    out = run("mujhe seene mein dard hai aur chakkar")
    assert out["risk_level"] == "red" and out["response_type"] == "emergency"
    assert "1122" in out["final_response"]


def test_clarify_then_guidance(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", fake({**BASE, "critical_missing": ["fainting?"]}, clarify=["Kya aap behosh hue?"]))
    out = run("chakkar aa rahe hain")
    assert out["response_type"] == "clarify" and out["clar_rounds"] == 1
    out = run("chakkar aa rahe hain", force_answer=True)
    assert out["response_type"] == "guidance" and out["risk_level"] == "green"
    assert out["case_summary"]


def test_audit_failure_falls_back(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", fake(BASE, audit_pass=False))
    out = run("chakkar aa rahe hain")
    assert out["response_type"] == "fallback" and out["attempts"] == 2


def test_fainting_is_never_green(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", fake({**BASE, "symptoms": ["fainting"], "scenario_ids": ["fainting"]}))
    out = run("meri behen behosh ho gayi thi", force_answer=True)
    assert out["risk_level"] == "yellow"


def test_llm_emergency_overrides(monkeypatch):
    monkeypatch.setattr(llm, "chat_json", fake({**BASE, "emergency_suspected": True, "emergency_reason": "x"}))
    assert run("kuch ajeeb sa hai")["response_type"] == "emergency"
