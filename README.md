# 🩺 Sahaara AI

Multilingual (English / Urdu / Roman Urdu) agentic early-health-support and care-navigation platform.
**Understand → Screen → Support → Escalate → Navigate.** Built with **Streamlit + Groq + LangGraph + RAG (FAISS)**.

> **Don't diagnose. Don't dismiss. Don't delay.**
> Sahaara does not diagnose or replace a doctor. This is a hackathon prototype; the knowledge base is a **draft that must be clinically reviewed** before any real-world use.

## Quick start

```bash
git clone <your-repo-url> && cd sahaara-ai
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # then put your GROQ_API_KEY inside
streamlit run app.py
```

Lightweight mode (no torch / sentence-transformers download, keyword retrieval instead of FAISS):
`SAHAARA_EMBEDDINGS=off streamlit run app.py`

**Streamlit Community Cloud:** push to GitHub, create the app, and add `GROQ_API_KEY = "..."` under *Settings → Secrets*.

## How it works

```
user text / voice (Groq Whisper) / report upload
        │
 Patient Understanding ─► Measurement ─► Symptom Context ─► Triage / Safety (rules + LLM)
                                                               │
                  RED ──────────────────────────────────────────┤──► Escalation (static, multilingual) ─┐
                  missing critical info ─► Clarification (≤3 questions, ≤2 rounds) ─► (ends turn)       │
                  otherwise ─► Evidence/RAG ─► Early Support ─► Referral ─► Health Literacy ─► Safety Auditor
                                                       ▲                                        │ fail
                                                       └──────── one retry ◄────────────────────┤
                                                                                   fail twice ─► Safe fallback
                                                                                   pass ─► Finalize ─► Case Summary
```

| Agent | File / function | LLM? |
|---|---|---|
| Orchestrator | `graph.py` (LangGraph routing) | no |
| Patient Understanding | `agents.understanding_agent` | yes |
| Measurement (measured vs. guessed) | `agents.measurement_agent`, `rules.py` | no |
| Symptom Context | `agents.context_agent` | no |
| Triage / Safety | `agents.triage_agent`, `rules.py` | rules first; LLM can only escalate |
| Clarification | `agents.clarification_agent` | yes |
| Evidence Retrieval (RAG) | `rag.py`, `knowledge/scenarios.json` | embeddings |
| Early Support | `agents.support_agent` | yes (grounded in evidence only) |
| Referral | `agents.referral_agent` | no |
| Health Literacy | `agents.literacy_agent` | yes |
| Case Summary | `agents.summary_agent` | no |
| Document | `agents.document_agent` (sidebar upload, PDF/txt) | yes |
| Final Safety Auditor | `agents.audit_agent` + `rules.audit_bundle` | rules + LLM |

Not yet built (Phase 2): Follow-up tracking agent with reminders, image/OCR documents, offline mode.

## Safety design

1. **Rule-based red flags** (`rules.py`) in English, Roman Urdu and Urdu script with negation handling ("chest pain nahi hai"). Hard rules override the LLM.
2. **LLM can only raise risk**, never lower it (`emergency_suspected`, `needs_evaluation`).
3. **Emergency path is static**: pre-written messages in 3 languages, no LLM or translation involved.
4. **Fainting is never "green"**; measured values (glucose, BP, temperature, SpO2, pulse) are evaluated against thresholds.
5. **RAG grounding**: early-support steps must come from retrieved scenario text; sources and versions are shown.
6. **Auditor**: deterministic checks (no doses, no stop/change medicine, no "you have X") plus an LLM review that also compares translation against English. Fails twice → safe generic referral.

## Project structure

```
app.py                 Streamlit UI (chat, voice, shortcuts, report upload, agent trace)
sahaara/
  config.py  llm.py  state.py  graph.py  agents.py  rules.py  rag.py  i18n.py
knowledge/scenarios.json   12 scenarios (symptom patterns, red flags, early support, sources)
tests/                 pytest: safety rules + end-to-end graph with mocked LLM (no API key needed)
```

Run tests: `SAHAARA_EMBEDDINGS=off pytest -q`

## Before real-world use (important)

- Have clinicians review/replace `knowledge/scenarios.json` with verified WHO / national guideline text (each entry has `source` and `source_date`).
- Review the thresholds in `rules.py` and the emergency numbers (`SAHAARA_EMERGENCY`, default `1122 / 115`).
- Build an evaluation set (red-flag recall, grounding, Urdu meaning preservation) from the metrics in the product spec.
- Add privacy/consent handling; health data is sensitive.
