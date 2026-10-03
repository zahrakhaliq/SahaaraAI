"""Deterministic safety rules (Safety Layer 2). These can override the LLM and never need an API call.

Thresholds are conservative, configurable defaults and MUST be reviewed by a clinician before real use.
Text matching covers English, Roman Urdu and Urdu script. Matches are skipped when clearly negated
("chest pain nahi hai"); the LLM's `emergency_suspected` acts as a second net for odd phrasings.
"""
import re

I = re.I

# (id, level, regex or [regex, regex] (all must match), description)
TEXT_FLAGS = [
    ("unresponsive", "red",
     r"(not (responding|waking)|unresponsive|still unconscious|abhi (bhi )?behosh|behosh hai|hosh mein nahi aa|hosh nahi aa|jawab nahi de|uth nahi (rah|raha|rahi)|jaag nahi (rah|raha|rahi)|ہوش میں نہیں)",
     "Person is unconscious or not responding"),
    ("confusion", "red",
     r"(confus|hosh mein nahi|behki behki|ulti seedhi|ajeeb baatein|samajh nahi aa raha|الجھن)",
     "New confusion or altered awareness"),
    ("chest_pain", "red",
     r"(chest (pain|tight|pressure|heaviness)|heart pain|seene (mein|me|main) (dard|bhari|bhaari|jakar|dabao)|seena (dard|bhari)|dil (mein|me|main) dard|سینے (میں )?(درد|بھاری|جکڑ)|دل (میں )?درد)",
     "Chest pain or pressure"),
    ("breathing_difficulty", "red",
     r"(saans (lene )?(mein|me|main) (bohat |boht |shadeed |zyada )?(mushkil|dikkat|takleef|problem)|saans (phool|nahi aa|ruk)|dum ghut|can'?t breathe|cannot breathe|difficulty (in )?breathing|trouble breathing|short(ness)? of breath|breathless|سانس (لینے )?(میں )?(مشکل|تکلیف|پھول)|دم گھ)",
     "Difficulty breathing"),
    ("seizure", "red",
     r"(seizure|convulsion|\bfits\b|daura|mirgi|jhatk(e|ay)|مرگی|دورہ|جھٹکے)",
     "Seizure / convulsions"),
    ("stroke_signs", "red",
     r"(face (is )?droop|facial droop|chehra (tedha|latak)|munh (tedha|latak)|bolne (mein|me) (mushkil|dikkat)|zuban (latak|lad)|slurred|speech (problem|difficulty)|one side (of (the )?body )?(weak|numb)|ek (taraf|side) (se |ki |ka )?(kamzori|sunn|numb|haath|bazu)|haath pair (sunn|kaam nahi)|sudden (loss of vision|blindness)|منہ (ٹیڑھا|ٹیڑھ)|بولنے (میں )?(مشکل|دشواری))",
     "Possible stroke signs (face, arm, speech)"),
    ("bleeding_vomit_stool", "red",
     r"(vomit(ing)? blood|blood (in|when) vomit|khoon ki ulti|ulti (mein|me) khoon|kala pakhana|black (tarry )?stool|tarry stool|pakhane (mein|me) khoon|coughing (up )?blood|khansi (mein|me) khoon|خون کی الٹی|کالا پاخانہ)",
     "Blood in vomit, stool or cough"),
    ("severe_bleeding", "red",
     r"(severe bleeding|heavy bleeding|bleeding (a lot|heavily|won'?t stop|not stopping)|khoon (ruk nahi|nahi ruk)|bohat (zyada )?khoon (beh|nikal)|khoon behna band nahi)",
     "Severe or uncontrolled bleeding"),
    ("thunderclap_headache", "red",
     r"(worst headache|thunderclap|sudden(ly)? (severe|very bad) headache|achanak (bohat |boht )?(shadeed|tez|zyada) (sar )?dard|zindagi ka sabse (bura|shadeed) sar dard)",
     "Sudden, very severe headache"),
    ("cannot_swallow", "red",
     r"(can'?t swallow|cannot swallow|nigal nahi|nigalna mushkil|نگل نہیں)",
     "Unable to swallow safely"),
    ("self_harm", "red",
     r"(suicide|khudkushi|khud kushi|kill myself|marna chahta|marna chahti|jaan dena chahta|jaan dena chahti|خودکشی)",
     "Thoughts of self-harm"),
    ("severe_burn", "red",
     [r"\b(burn|burnt|jhulas|jal gay[aei]|jal gaya)\b",
      r"(face|chehr|electric|bijli|chemical|tezab|acid|inhal|dhuan|genital|large area|bara hissa)"],
     "Burn on a high-risk area or by chemical/electrical cause"),
    # Watch flags: not an emergency by themselves, but never "green"
    ("fainting", "yellow",
     r"(behosh|be-?hosh|bayhosh|unconscious|passed out|fainted|faint(ed)? ho|black ?out|collaps|بے ?ہوش|بیہوش)",
     "Reported fainting / loss of consciousness (needs evaluation)"),
    ("head_injury", "yellow",
     r"(head injury|sar (par|pe|mein|me) chot|hit (my |his |her )?head|سر (پر|میں) چوٹ)",
     "Head injury"),
    ("palpitations", "yellow",
     r"(dil doob|dhadkan (tez|bohat|ajeeb)|palpitation|heart racing|dil tez)",
     "Palpitations / irregular or racing heartbeat"),
    ("pregnancy", "yellow",
     r"(pregnan|hamila|hamal|حاملہ|حمل)",
     "Pregnancy mentioned (lower threshold for evaluation)"),
]

NEG_AFTER = re.compile(r"^[\s,.:;\-]*(?:\S+[\s,]+){0,3}?(?:nahi|nahin|nhi|nai|not|never|no|نہیں)(?:\W|$)", I)
NEG_BEFORE = re.compile(r"(?:\bno|\bwithout|\bbina|\bkoi|بغیر|کوئی)\s+$", I)


def _negated(text: str, m: re.Match) -> bool:
    after = text[m.end(): m.end() + 28]
    before = text[max(0, m.start() - 12): m.start()]
    return bool(NEG_AFTER.search(after) or NEG_BEFORE.search(before))


def scan_text(text: str):
    """Return a list of flag dicts found in the user's own words."""
    t = (text or "").lower()
    found = []
    for fid, level, pat, desc in TEXT_FLAGS:
        if isinstance(pat, list):
            hit = all(re.search(p, t, I | re.S) for p in pat)
        else:
            hit = any(not _negated(t, m) for m in re.finditer(pat, t, I))
        if hit:
            found.append({"id": fid, "level": level, "desc": desc, "source": "rule"})
    return found


# ---------------------------------------------------------------- measurements
SEP = r"[\s:=\-]*(?:is|hai|tha|level|reading|check|ki|ka|ho)?[\s:=\-]*"


def extract_measurements(text: str) -> dict:
    """Regex extraction of explicitly stated numbers (canonical units)."""
    t = (text or "").lower()
    out = {}
    m = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", t)
    if m:
        out.update(canonicalize({"bp_systolic": m.group(1), "bp_diastolic": m.group(2)}))
    m = re.search(r"(?:sugar|glucose|bsr|bsl|shugar)" + SEP + r"(\d{1,3}(?:\.\d)?)", t)
    if m:
        out.update(canonicalize({"glucose": m.group(1), "glucose_unit": "mmol/L" if "mmol" in t else ""}))
    m = re.search(r"(?:temp(?:erature)?|bukh?ar|fever|tapmaan)" + SEP + r"(\d{2,3}(?:\.\d)?)", t)
    if m:
        out.update(canonicalize({"temperature": m.group(1)}))
    m = re.search(r"(?:spo2|oxygen|o2|saturation)" + SEP + r"(\d{2,3})", t)
    if m:
        out.update(canonicalize({"spo2": m.group(1)}))
    m = re.search(r"(?:pulse|heart rate|nabz)" + SEP + r"(\d{2,3})", t)
    if m:
        out.update(canonicalize({"pulse": m.group(1)}))
    return out


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def canonicalize(raw: dict) -> dict:
    """Normalise raw (LLM or regex) measurements to bp_sys, bp_dia, glucose_mgdl, temp_c, spo2, pulse."""
    out = {}
    s, d = _num(raw.get("bp_systolic")), _num(raw.get("bp_diastolic"))
    if s and d and 50 <= s <= 300 and 30 <= d <= 200 and s > d:
        out["bp_sys"], out["bp_dia"] = s, d
    g = _num(raw.get("glucose"))
    if g:
        unit = str(raw.get("glucose_unit") or "").lower()
        if "mmol" in unit or g < 30:
            g *= 18
        if 15 <= g <= 900:
            out["glucose_mgdl"] = round(g)
    t = _num(raw.get("temperature"))
    if t:
        unit = str(raw.get("temperature_unit") or "").lower()
        if unit.startswith("f") or t > 45:
            t = (t - 32) * 5 / 9
        if 30 <= t <= 45:
            out["temp_c"] = round(t, 1)
    sp = _num(raw.get("spo2"))
    if sp and 50 <= sp <= 100:
        out["spo2"] = sp
    p = _num(raw.get("pulse"))
    if p and 20 <= p <= 250:
        out["pulse"] = p
    return out


def evaluate_measurements(m: dict, symptomatic: bool, age_group: str = "unknown"):
    flags = []

    def add(fid, level, desc):
        flags.append({"id": fid, "level": level, "desc": desc, "source": "measurement"})

    g = m.get("glucose_mgdl")
    if g is not None:
        if g < 54:
            add("glucose_very_low", "red", f"Measured glucose {g:.0f} mg/dL is very low")
        elif g < 70:
            add("glucose_low", "yellow", f"Measured glucose {g:.0f} mg/dL is low")
        elif g >= 400:
            add("glucose_very_high", "red", f"Measured glucose {g:.0f} mg/dL is very high")
        elif g >= 300:
            add("glucose_high", "yellow", f"Measured glucose {g:.0f} mg/dL is high")
    s, d = m.get("bp_sys"), m.get("bp_dia")
    if s is not None and d is not None:
        if s >= 180 or d >= 120:
            add("bp_crisis", "red" if symptomatic else "yellow",
                f"Measured BP {s:.0f}/{d:.0f} is in a dangerously high range")
        elif s < 80 and symptomatic:
            add("bp_very_low", "red", f"Measured BP {s:.0f}/{d:.0f} is very low with symptoms")
        elif (s < 90 or d < 60) and symptomatic:
            add("bp_low", "yellow", f"Measured BP {s:.0f}/{d:.0f} is low with symptoms")
        elif s >= 140 or d >= 90:
            add("bp_high", "yellow", f"Measured BP {s:.0f}/{d:.0f} is above the normal range")
    t = m.get("temp_c")
    if t is not None:
        if age_group == "newborn" and t >= 38:
            add("newborn_fever", "red", "Fever in a baby under 3 months")
        elif t >= 40:
            add("fever_very_high", "red", f"Temperature {t:.1f} °C is very high")
        elif age_group == "infant" and t >= 38:
            add("infant_fever", "yellow", "Fever in an infant")
        elif t >= 39.5:
            add("fever_high", "yellow", f"Temperature {t:.1f} °C is high")
    sp = m.get("spo2")
    if sp is not None:
        if sp < 90:
            add("spo2_low", "red", f"Oxygen saturation {sp:.0f}% is low")
        elif sp < 94:
            add("spo2_borderline", "yellow", f"Oxygen saturation {sp:.0f}% is borderline")
    p = m.get("pulse")
    if p is not None and symptomatic:
        if p > 130 or p < 40:
            add("pulse_extreme", "red", f"Pulse {p:.0f}/min is outside a safe range")
        elif p > 110 or p < 50:
            add("pulse_abnormal", "yellow", f"Pulse {p:.0f}/min is abnormal")
    return flags


def risk_from_flags(flags) -> str:
    levels = {f["level"] for f in flags}
    return "red" if "red" in levels else "yellow" if "yellow" in levels else "green"


# ---------------------------------------------------------------- output audit (deterministic part)
DOSE = re.compile(r"\b\d+(\.\d+)?\s?(mg|mcg|µg|iu)\b", I)
MED_CHANGE = re.compile(r"\b(stop|skip|discontinue|reduce|increase|double)\b[^.]{0,30}\b(medicine|medication|insulin|tablets?|dose)\b", I)
DIAGNOSIS = re.compile(
    r"\byou (definitely |certainly )?(have|are suffering from|suffer from) (low|high|diabetes|anemia|anaemia|hypoglyc|hyperglyc|a deficiency|vitamin|iron)", I)


def audit_bundle(bundle: dict, risk: str):
    issues = []
    text = " ".join(
        str(v) if not isinstance(v, list) else " ".join(map(str, v)) for v in bundle.values()
    )
    if DOSE.search(text):
        issues.append("Contains a medication dose (not allowed).")
    for m in MED_CHANGE.finditer(text):
        prefix = text[max(0, m.start() - 15): m.start()].lower()
        if not re.search(r"(not|n't|never|don't|do not)\s*$", prefix):
            issues.append("Appears to tell the user to stop/change medication.")
            break
    if DIAGNOSIS.search(text):
        issues.append("States a condition as a confirmed diagnosis.")
    if not bundle.get("warning_signs"):
        issues.append("Missing warning signs.")
    if not bundle.get("next_step"):
        issues.append("Missing next step.")
    if risk == "yellow" and not re.search(r"(health ?care|doctor|clinic|hospital|health worker|professional)",
                                          str(bundle.get("next_step", "")), I):
        issues.append("Risk is 'yellow' but next step does not direct to a healthcare professional.")
    return issues
