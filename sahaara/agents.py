"""Sahaara agents. Each function is a LangGraph node: it takes the shared state and returns a partial update."""
import json

from . import config, i18n, llm, rag, rules

LANG_NAMES = {
    "en": "simple English",
    "ur": "Urdu in Urdu (Arabic) script",
    "roman_ur": "Roman Urdu (Urdu written in Latin letters, the way people text it)",
}
AGE_GROUPS = {"newborn", "infant", "child", "adult", "older_adult", "unknown"}


def _t(state, agent, note):
    return state.get("trace", []) + [{"agent": agent, "note": note}]


def _lang(state):
    return state.get("language") if state.get("language") in i18n.LANGS else "roman_ur"


# =====================================================================================
# Agent 2: Patient Understanding
# =====================================================================================
UNDERSTAND_SYSTEM = """You are the Patient Understanding Agent of Sahaara AI, a health-support tool for people with limited access to care.
The user writes in English, Urdu script or Roman Urdu (Urdu in Latin letters). Convert the conversation into structured data.
Return ONLY a JSON object with these keys:
- language: "en", "ur" or "roman_ur" (the language of the user's MOST RECENT message)
- age_group: "newborn" (<3 months), "infant" (<1 year), "child", "adult", "older_adult", or "unknown" (for the patient, who may be someone else)
- symptoms: list of short English phrases
- duration: short English string or ""
- severity: "mild", "moderate", "severe" or "unknown"
- measurements: object with numeric values ONLY if explicit numbers were stated: bp_systolic, bp_diastolic, glucose, glucose_unit ("mg/dL" or "mmol/L"), temperature, temperature_unit ("C" or "F"), spo2, pulse. Use null otherwise.
- medical_history: list, medications: list (only what the user stated or uploaded documents show)
- user_hypotheses: list of the user's own guesses (e.g. "low sugar", "vitamin D deficiency"). A guess like "BP high lag raha hai" is a hypothesis, NOT a measurement.
- scenario_ids: up to 3 ids from the allowed list that match the concern
- critical_missing: up to 3 short English items whose answer would materially change safety or next steps and are NOT yet known (empty list if enough is known)
- emergency_suspected: true if the described situation could be a life-threatening emergency (use medical judgment; respect negations like "no chest pain")
- emergency_reason: short English reason or ""
- needs_evaluation: true if a healthcare professional should assess this soon even without emergency signs (e.g. symptoms > 3 days, vulnerable patient, fainting, abnormal measured values, chronic illness)
- evaluation_reason: short English reason or ""
Never diagnose. Never invent facts."""


def understanding_agent(state):
    docs = json.dumps(state.get("documents") or [], ensure_ascii=False)[:3000]
    user = (f"ALLOWED scenario_ids: {rag.scenario_ids()}\n\nCONVERSATION:\n{state['transcript']}\n\n"
            f"UPLOADED DOCUMENT SUMMARIES:\n{docs}")
    try:
        d = llm.chat_json(UNDERSTAND_SYSTEM, user, max_tokens=900)
    except Exception as e:
        d = {}
        note = f"LLM error: {e}"
    else:
        note = f"symptoms={d.get('symptoms')}, scenarios={d.get('scenario_ids')}"
    lang = state.get("language_override") or d.get("language")
    age = d.get("age_group") if d.get("age_group") in AGE_GROUPS else "unknown"
    valid = set(rag.scenario_ids())
    return {
        "language": lang if lang in i18n.LANGS else "roman_ur",
        "age_group": age,
        "symptoms": d.get("symptoms") or [],
        "duration": d.get("duration") or "",
        "severity": d.get("severity") or "unknown",
        "measurements_raw": d.get("measurements") or {},
        "medical_history": d.get("medical_history") or [],
        "medications": d.get("medications") or [],
        "user_hypotheses": d.get("user_hypotheses") or [],
        "scenario_ids": [s for s in (d.get("scenario_ids") or []) if s in valid][:3],
        "critical_missing": d.get("critical_missing") or [],
        "emergency_suspected": bool(d.get("emergency_suspected")),
        "emergency_reason": d.get("emergency_reason") or "",
        "needs_evaluation": bool(d.get("needs_evaluation")),
        "evaluation_reason": d.get("evaluation_reason") or "",
        "trace": _t(state, "Patient Understanding", note),
    }


# =====================================================================================
# Agent 9: Measurement (measured value vs. user's guess)
# =====================================================================================
def measurement_agent(state):
    from_text = rules.extract_measurements(state.get("user_text", ""))
    from_llm = rules.canonicalize(state.get("measurements_raw") or {})
    merged = {**from_llm, **from_text}  # explicit regex hits win over LLM guesses
    return {"measurements": merged,
            "trace": _t(state, "Measurement", f"measured values: {merged or 'none provided'}")}


# =====================================================================================
# Agent 4: Symptom Context (preserves uncertainty)
# =====================================================================================
def context_agent(state):
    kb = rag.get_kb()
    ids = list(state.get("scenario_ids") or [])
    if not ids:
        ids = kb.search_scenarios(" ".join(state.get("symptoms") or []) + " " + state.get("user_text", ""), k=2)
    ctx = []
    for sid in ids:
        for c in kb.scenarios[sid]["possible_contexts"]:
            if c not in ctx:
                ctx.append(c)
    return {"scenario_ids": ids, "possible_contexts": ctx[:10],
            "trace": _t(state, "Symptom Context", f"scenarios={ids}")}


# =====================================================================================
# Agent 5: Triage / Safety (rules first, LLM can only escalate further)
# =====================================================================================
def triage_agent(state):
    flags = rules.scan_text(state.get("user_text", ""))
    symptomatic = bool(state.get("symptoms"))
    flags += rules.evaluate_measurements(state.get("measurements", {}), symptomatic, state.get("age_group", "unknown"))
    if state.get("emergency_suspected"):
        flags.append({"id": "llm_emergency", "level": "red", "source": "llm",
                      "desc": state.get("emergency_reason") or "Possible emergency identified"})
    fever_words = " ".join(state.get("symptoms") or []).lower() + " " + state.get("user_text", "").lower()
    if state.get("age_group") == "newborn" and ("fever" in fever_words or "bukhar" in fever_words or "بخار" in fever_words):
        flags.append({"id": "newborn_fever", "level": "red", "source": "rule", "desc": "Fever in a baby under 3 months"})
    if state.get("needs_evaluation") and not any(f["level"] in ("red", "yellow") for f in flags):
        flags.append({"id": "needs_evaluation", "level": "yellow", "source": "llm",
                      "desc": state.get("evaluation_reason") or "Healthcare evaluation advisable"})
    seen, uniq = set(), []
    for f in flags:
        if f["id"] not in seen:
            seen.add(f["id"])
            uniq.append(f)
    risk = rules.risk_from_flags(uniq)
    return {"flags": uniq, "red_flags": [f["desc"] for f in uniq if f["level"] == "red"], "risk_level": risk,
            "trace": _t(state, "Triage / Safety", f"risk={risk}; flags={[f['id'] for f in uniq]}")}


def route_after_triage(state):
    if state["risk_level"] == "red":
        return "escalate"
    if (state.get("critical_missing") and not state.get("force_answer")
            and state.get("clar_rounds", 0) < config.MAX_CLARIFY_ROUNDS):
        return "clarify"
    return "retrieve"


# =====================================================================================
# Escalation (static, multilingual, no LLM)
# =====================================================================================
def escalation_node(state):
    lang = _lang(state)
    ids = {f["id"] for f in state.get("flags", [])}
    nums = config.EMERGENCY_NUMBERS
    parts = [i18n.SELF_HARM[lang].format(numbers=nums)] if "self_harm" in ids else []
    parts.append(i18n.EMERGENCY[lang].format(numbers=nums))
    for fid, tip in i18n.FLAG_TIPS.items():
        if fid in ids:
            parts.append("➡️ " + tip[lang])
    reasons = "; ".join(state.get("red_flags") or [])
    if reasons:
        parts.append(f"_Reason (English): {reasons}_")
    return {"final_response": "\n\n".join(parts), "response_type": "emergency",
            "trace": _t(state, "Escalation", "static emergency message; normal workflow interrupted")}


# =====================================================================================
# Agent 3: Clarification (smallest useful set of questions)
# =====================================================================================
CLARIFY_SYSTEM = """You are the Clarification Agent of Sahaara AI. Ask the SMALLEST number (1 to 3) of short questions whose answers
would most change safety or the next step. Rules: never ask what is already known; prefer yes/no or numeric questions;
put the most safety-relevant question first; use the candidate questions as inspiration; write questions in {lang};
simple everyday words. Return ONLY JSON: {{"questions": ["...", "..."]}}. If nothing important is missing return {{"questions": []}}."""


def clarification_agent(state):
    kb = rag.get_kb()
    candidates = []
    for sid in state.get("scenario_ids", []):
        candidates += kb.scenarios[sid]["important_questions"]
    user = json.dumps({
        "conversation": state["transcript"], "already_known": {
            "symptoms": state.get("symptoms"), "duration": state.get("duration"),
            "measurements": state.get("measurements"), "age_group": state.get("age_group")},
        "critical_missing": state.get("critical_missing"), "candidate_questions": candidates[:12]},
        ensure_ascii=False)
    lang = _lang(state)
    try:
        qs = llm.chat_json(CLARIFY_SYSTEM.format(lang=LANG_NAMES[lang]), user, max_tokens=400).get("questions") or []
    except Exception:
        qs = []
    qs = [q for q in qs if isinstance(q, str) and q.strip()][:3]
    if not qs:
        return {"questions": [], "trace": _t(state, "Clarification", "no extra questions needed")}
    body = "\n".join(f"{i}. {q}" for i, q in enumerate(qs, 1))
    text = f"{i18n.CLARIFY_INTRO[lang]}\n\n{body}\n\n_{i18n.CLARIFY_OUTRO[lang]}_"
    return {"questions": qs, "final_response": text, "response_type": "clarify",
            "clar_rounds": state.get("clar_rounds", 0) + 1,
            "trace": _t(state, "Clarification", f"asked {len(qs)} question(s)")}


def route_after_clarify(state):
    return "end" if state.get("questions") else "retrieve"


# =====================================================================================
# Agent 6: Evidence Retrieval (RAG)
# =====================================================================================
def retrieval_agent(state):
    ev = rag.get_kb().evidence(state.get("scenario_ids", []))
    return {"retrieved_evidence": ev,
            "trace": _t(state, "Evidence Retrieval (RAG)", f"{len(ev)} chunks from {state.get('scenario_ids')}")}


# =====================================================================================
# Agent 7: Early Support (content, English, grounded)
# =====================================================================================
SUPPORT_SYSTEM = """You are the Early Support Agent of Sahaara AI, a safety-first tool for people with limited access to care.
You NEVER diagnose and NEVER prescribe. Write in simple English (it will be translated later). Return ONLY a JSON object with keys:
- understood: 1-2 sentences restating what the person said, including duration.
- relevant: a short paragraph saying these symptoms "can be associated with several causes" and naming 2-4 possibilities taken ONLY from POSSIBLE CONTEXTS / EVIDENCE. Treat the user's own guesses as unconfirmed; never write "you have <condition>".
- to_check: list (0-4) of useful measurements or observations not yet available (BP, glucose, temperature, etc.).
- do_now: list (2-5) of safe early-support steps taken ONLY from EVIDENCE. If a step in EVIDENCE has a condition (e.g. awake and able to swallow), keep that condition in the sentence.
- warning_signs: list (3-6) of concrete red flags from EVIDENCE that apply to this case.
- follow_up: what to monitor and what to do if it does not improve.
Rules: no medicine doses; never tell anyone to start, stop or change prescribed medicines; if a measured value is given, explain it only as far as EVIDENCE allows, otherwise say a clinician should interpret it; if risk_level is "yellow" state clearly that a healthcare professional should evaluate; never promise the person is safe; short sentences."""


def support_agent(state):
    ev = "\n".join(
        f"[{i}] {c['scenario']} / {c['section']} (source: {c['source']}, {c['source_date']}): {c['text']}"
        for i, c in enumerate(state.get("retrieved_evidence", []), 1))
    case = {k: state.get(k) for k in ("age_group", "symptoms", "duration", "severity", "measurements",
                                      "medical_history", "medications", "user_hypotheses")}
    issues = (state.get("audit") or {}).get("issues") or []
    user = (f"CASE: {json.dumps(case, ensure_ascii=False)}\nRISK LEVEL: {state['risk_level']}\n"
            f"FLAGS: {[f['desc'] for f in state.get('flags', [])]}\n"
            f"POSSIBLE CONTEXTS: {state.get('possible_contexts')}\n\nEVIDENCE:\n{ev}\n\n"
            f"FIX THESE ISSUES FROM THE PREVIOUS ATTEMPT: {issues}")
    try:
        d = llm.chat_json(SUPPORT_SYSTEM, user, temperature=0.2, max_tokens=1400)
    except Exception as e:
        d = {}
    bundle = {
        "understood": str(d.get("understood") or ""),
        "relevant": str(d.get("relevant") or ""),
        "to_check": [str(x) for x in (d.get("to_check") or [])],
        "do_now": [str(x) for x in (d.get("do_now") or [])],
        "warning_signs": [str(x) for x in (d.get("warning_signs") or [])],
        "follow_up": str(d.get("follow_up") or ""),
    }
    return {"bundle_en": bundle, "attempts": state.get("attempts", 0) + 1,
            "trace": _t(state, "Early Support", f"attempt {state.get('attempts', 0) + 1}")}


# =====================================================================================
# Agent 11: Referral (deterministic: explains WHY and what to bring)
# =====================================================================================
def referral_agent(state):
    kb = rag.get_kb()
    notes = [kb.scenarios[s]["referral_note"] for s in state.get("scenario_ids", []) if s in kb.scenarios][:2]
    reasons = [f["desc"] for f in state.get("flags", []) if f["level"] == "yellow"]
    if state["risk_level"] == "yellow":
        why = f" Reason: {'; '.join(reasons)}." if reasons else ""
        next_step = ("Please arrange to be seen by a healthcare professional today (nearest clinic, health centre or hospital)."
                     + why + (" " + " ".join(notes) if notes else ""))
    else:
        next_step = ("You can monitor this at home for now. If it is not improving within 48 hours (24 hours for children, "
                     "older adults or pregnancy), gets worse, or any warning sign appears, see a healthcare professional.")
    bring = ["Notes of your symptoms and when they started"]
    if state.get("measurements"):
        bring.append("Your BP / glucose / temperature readings with the time taken")
    bring.append("All medicines you take (or the packets)")
    bring.append("Any previous reports or prescriptions")
    bundle = dict(state.get("bundle_en") or {})
    bundle["next_step"] = next_step
    bundle["bring_to_doctor"] = bring
    return {"bundle_en": bundle,
            "referral": {"level": state["risk_level"], "next_step": next_step},
            "trace": _t(state, "Referral", f"level={state['risk_level']}")}


# =====================================================================================
# Agent 8: Health Literacy (language + simplicity, preserves facts)
# =====================================================================================
LITERACY_SYSTEM = """You are the Health Literacy Agent. Rewrite every string value of the JSON into {lang} using short, everyday words
for a person with low health literacy. Keep the keys and list structure unchanged. Preserve EVERY fact, number, unit, condition and warning
exactly; add nothing; remove nothing. Keep familiar terms such as BP, sugar, glucose, ORS, CPR, SpO2 as people say them.
Return ONLY the JSON object."""


def literacy_agent(state):
    lang = _lang(state)
    bundle = state.get("bundle_en") or {}
    if lang == "en" or not bundle:
        return {"bundle_final": bundle, "trace": _t(state, "Health Literacy", "English: no rewrite needed")}
    try:
        out = llm.chat_json(LITERACY_SYSTEM.format(lang=LANG_NAMES[lang]),
                            json.dumps(bundle, ensure_ascii=False), temperature=0.1, max_tokens=2000)
        if set(out.keys()) >= set(bundle.keys()):
            return {"bundle_final": out, "trace": _t(state, "Health Literacy", f"rewritten in {lang}")}
    except Exception:
        pass
    return {"bundle_final": {}, "trace": _t(state, "Health Literacy", "rewrite failed")}


# =====================================================================================
# Agent 14: Final Safety Auditor
# =====================================================================================
AUDIT_SYSTEM = """You are the Final Safety Auditor of a health-support app. Review the OUTPUT against the EVIDENCE.
FAIL only for real safety problems: (1) a possibility stated as a confirmed diagnosis; (2) medication doses or instructions to start/stop/change medicines;
(3) advice not supported by the evidence, or contradicting it; (4) missing or weakened warning signs, or false reassurance for the stated risk level;
(5) the translated OUTPUT_FINAL changing the meaning, numbers or warnings of OUTPUT_ENGLISH (skip if identical).
Return ONLY JSON: {{"pass": true|false, "issues": ["short description", ...]}}."""


def audit_agent(state):
    bundle = state.get("bundle_en") or {}
    final = state.get("bundle_final") or {}
    issues = rules.audit_bundle(bundle, state["risk_level"])
    if not final:
        issues.append("Final-language version missing.")
    if not issues:
        ev = "\n".join(c["text"] for c in state.get("retrieved_evidence", []))
        user = json.dumps({"risk_level": state["risk_level"], "EVIDENCE": ev, "OUTPUT_ENGLISH": bundle,
                           "OUTPUT_FINAL": final if final != bundle else "identical"}, ensure_ascii=False)
        try:
            res = llm.chat_json(AUDIT_SYSTEM, user, temperature=0.0, max_tokens=500)
            if res.get("pass") is not True:
                issues += [str(i) for i in (res.get("issues") or ["Auditor did not approve."])]
        except Exception as e:
            issues.append(f"Auditor unavailable: {e}")
    ok = not issues
    return {"audit": {"pass": ok, "issues": issues},
            "trace": _t(state, "Safety Auditor", "PASS" if ok else f"FAIL: {issues}")}


def route_after_audit(state):
    if state["audit"]["pass"]:
        return "finalize"
    return "support" if state.get("attempts", 0) < config.MAX_SUPPORT_ATTEMPTS else "fallback"


def fallback_node(state):
    lang = _lang(state)
    return {"final_response": i18n.FALLBACK[lang].format(numbers=config.EMERGENCY_NUMBERS), "response_type": "fallback",
            "trace": _t(state, "Fallback", "audit failed twice: safe generic referral shown")}


# =====================================================================================
# Final rendering
# =====================================================================================
def finalize_node(state):
    lang = _lang(state)
    h = i18n.HEADINGS[lang]
    b = state["bundle_final"]

    def bullets(items):
        return "\n".join(f"- {x}" for x in items)

    sections = [f"**{i18n.RISK_BANNER[state['risk_level']][lang]}**"]
    for key, head in (("understood", "understood"), ("relevant", "relevant")):
        if b.get(key):
            sections.append(f"**{h[head]}**\n{b[key]}")
    for key, head in (("to_check", "to_check"), ("do_now", "do_now"), ("warning_signs", "warning_signs")):
        if b.get(key):
            sections.append(f"**{h[head]}**\n{bullets(b[key])}")
    if b.get("next_step"):
        sections.append(f"**{h['next_step']}**\n{b['next_step']}")
    if b.get("bring_to_doctor"):
        sections.append(f"**{h['bring']}**\n{bullets(b['bring_to_doctor'])}")
    if b.get("follow_up"):
        sections.append(f"**{h['follow_up']}**\n{b['follow_up']}")
    srcs = sorted({f"{c['source']} ({c['source_date']})" for c in state.get("retrieved_evidence", [])})
    if srcs:
        sections.append("_Sources: " + "; ".join(srcs) + "_")
    sections.append(f"_{i18n.DISCLAIMER[lang]}_")
    return {"final_response": "\n\n".join(sections), "response_type": "guidance",
            "trace": _t(state, "Finalize", "response rendered")}


# =====================================================================================
# Agent 12: Case Summary (for a healthcare professional; English; no LLM)
# =====================================================================================
def summary_agent(state):
    m = state.get("measurements") or {}
    bp = f"{m['bp_sys']:.0f}/{m['bp_dia']:.0f}" if "bp_sys" in m else "not available"
    gl = f"{m['glucose_mgdl']:.0f} mg/dL" if "glucose_mgdl" in m else "not available"
    tp = f"{m['temp_c']:.1f} C" if "temp_c" in m else "not available"
    sp = f"{m['spo2']:.0f}%" if "spo2" in m else "not available"
    lines = [
        "CASE SUMMARY (generated by Sahaara AI; not a diagnosis)",
        f"Patient: {state.get('age_group', 'unknown')}",
        f"Main concern: {', '.join(state.get('symptoms') or []) or 'not specified'}",
        f"Duration: {state.get('duration') or 'not specified'}   Severity: {state.get('severity', 'unknown')}",
        f"Measured values: BP {bp}; Glucose {gl}; Temperature {tp}; SpO2 {sp}",
        f"User's own assumption (unconfirmed): {', '.join(state.get('user_hypotheses') or []) or 'none'}",
        f"Relevant history: {', '.join(state.get('medical_history') or []) or 'not provided'}",
        f"Medications: {', '.join(state.get('medications') or []) or 'not provided'}",
        f"Red flags / alerts: {'; '.join(f['desc'] for f in state.get('flags', [])) or 'none identified in this interaction'}",
        f"Risk level assigned: {state.get('risk_level', 'unknown')}",
    ]
    return {"case_summary": "\n".join(lines), "trace": _t(state, "Case Summary", "generated")}


# =====================================================================================
# Agent 10: Document Agent (called from the UI when a report is uploaded)
# =====================================================================================
DOC_SYSTEM = """You are the Document Agent of Sahaara AI. Extract structured information from a medical document (lab report, prescription,
discharge summary). Do NOT interpret or diagnose. Return ONLY JSON with keys: document_type (string), medications (list of strings),
diagnoses_listed (list of strings written in the document), lab_values (list of {"test","value","unit","reference_range","flag"} using only what is printed),
summary (1-2 sentence neutral description)."""


def document_agent(text: str) -> dict:
    return llm.chat_json(DOC_SYSTEM, (text or "")[:9000], max_tokens=1200)
