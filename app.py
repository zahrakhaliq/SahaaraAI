import hashlib
import io
import json
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sahaara import agents, config, i18n, llm
from sahaara.graph import build_graph

st.set_page_config(page_title="Sahaara AI", page_icon="🩺", layout="centered")

CONCERNS = {
    "😵 Dizziness": "I am feeling dizzy",
    "🥱 Weakness": "I feel very weak and tired",
    "🍬 Blood Sugar": "Mera sugar low lag raha hai, paseena aa raha hai",
    "❤️ Blood Pressure": "Mera BP high lag raha hai aur sar dard hai",
    "🌡️ Fever": "Mujhe bukhar hai",
    "🤕 Headache": "Mujhe sar dard hai",
    "😮‍💨 Cough": "Mujhe khansi hai",
    "🤢 Vomiting/Diarrhea": "Ulti aur dast lag gaye hain",
    "💧 Dehydration": "Garmi se bohat pyaas aur kamzori hai",
    "😶‍🌫️ Fainting": "Meri behen achanak behosh ho gayi thi",
}
LANG_CHOICES = {"Auto-detect": None, "English": "en", "اردو (Urdu)": "ur", "Roman Urdu": "roman_ur"}


@st.cache_resource(show_spinner="Loading Sahaara agents and knowledge base...")
def get_graph():
    return build_graph()


def init_state():
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("clar_rounds", 0)
    st.session_state.setdefault("doc_context", [])
    st.session_state.setdefault("last_audio", None)
    st.session_state.setdefault("doc_key", None)


def extract_text(file) -> str:
    data = file.getvalue()
    if file.name.lower().endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    return data.decode("utf-8", errors="ignore")


def build_transcript(messages):
    lines = []
    for m in messages:
        if m["role"] == "user":
            lines.append(f"User: {m['content']}")
        elif m.get("type") == "clarify":
            lines.append(f"Sahaara asked: {m['content']}")
        else:
            lines.append("Sahaara: (gave guidance earlier in this conversation)")
    return "\n".join(lines)


def show_message(m, show_trace):
    with st.chat_message(m["role"], avatar="🩺" if m["role"] == "assistant" else None):
        if m.get("type") == "emergency":
            st.error(m["content"])
        else:
            st.markdown(m["content"])
        if m["role"] == "assistant":
            if m.get("case_summary"):
                with st.expander("📋 Summary to show your doctor"):
                    st.code(m["case_summary"], language=None)
            if show_trace and m.get("trace"):
                with st.expander("🤖 Agent activity"):
                    for step in m["trace"]:
                        st.markdown(f"**{step['agent']}**: {step['note']}")


def run_turn(text, lang_code, skip_questions):
    msgs = st.session_state.messages
    msgs.append({"role": "user", "content": text})
    state_in = {
        "transcript": build_transcript(msgs),
        "user_text": "\n".join(m["content"] for m in msgs if m["role"] == "user"),
        "language_override": lang_code,
        "clar_rounds": st.session_state.clar_rounds,
        "force_answer": skip_questions,
        "documents": st.session_state.doc_context,
        "trace": [],
    }
    with st.spinner("Sahaara agents are working..."):
        out = get_graph().invoke(state_in)
    rtype = out.get("response_type", "fallback")
    st.session_state.clar_rounds = out.get("clar_rounds", 0) if rtype == "clarify" else 0
    msgs.append({
        "role": "assistant", "content": out.get("final_response", ""), "type": rtype,
        "case_summary": out.get("case_summary"), "trace": out.get("trace", []),
    })


init_state()

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Settings")
    lang_label = st.selectbox("Reply language", list(LANG_CHOICES))
    skip_questions = st.checkbox("Skip follow-up questions", help="Get guidance with what I have already said.")
    show_trace = st.checkbox("Show agent activity", value=True)
    st.divider()
    st.subheader("📄 Upload report (optional)")
    up = st.file_uploader("Lab report / prescription (PDF or text)", type=["pdf", "txt"])
    if up is not None:
        key = (up.name, up.size)
        if st.session_state.doc_key != key and llm.has_key():
            with st.spinner("Reading document..."):
                try:
                    st.session_state.doc_context = [agents.document_agent(extract_text(up))]
                    st.session_state.doc_key = key
                except Exception as e:
                    st.error(f"Could not read document: {e}")
        if st.session_state.doc_context:
            with st.expander("Extracted information"):
                st.json(st.session_state.doc_context[0])
    st.divider()
    if st.button("🔄 New conversation"):
        for k in ("messages", "clar_rounds", "doc_context", "last_audio", "doc_key"):
            st.session_state.pop(k, None)
        st.rerun()
    st.caption(f"Emergency: {config.EMERGENCY_NUMBERS}")

# ------------------------------------------------------------------ main
st.title("🩺 Sahaara AI")
st.caption("Apni takleef apne alfaaz mein batayein. / Describe what you feel in your own words.")
st.info(i18n.DISCLAIMER["en"] + "  \n" + i18n.DISCLAIMER["roman_ur"], icon="ℹ️")

if not llm.has_key():
    st.error("GROQ_API_KEY is missing. Add it to a `.env` file or Streamlit secrets.")
    st.stop()

pending = None

if not st.session_state.messages:
    st.markdown("**What are you feeling?**")
    cols = st.columns(2)
    for i, (label, phrase) in enumerate(CONCERNS.items()):
        if cols[i % 2].button(label, use_container_width=True):
            pending = phrase

for m in st.session_state.messages:
    show_message(m, show_trace)

if hasattr(st, "audio_input"):
    audio = st.audio_input("🎤 Speak (Urdu / English)")
    if audio is not None:
        data = audio.getvalue()
        h = hashlib.md5(data).hexdigest()
        if h != st.session_state.last_audio:
            st.session_state.last_audio = h
            try:
                with st.spinner("Transcribing..."):
                    pending = llm.transcribe(data).strip() or None
            except Exception as e:
                st.error(f"Could not transcribe audio: {e}")

typed = st.chat_input("Yahan likhein / Type here...")
text = typed or pending

if text:
    with st.chat_message("user"):
        st.markdown(text)
    run_turn(text, LANG_CHOICES[lang_label], skip_questions)
    show_message(st.session_state.messages[-1], show_trace)
