from sahaara import rules


def ids(text):
    return {f["id"] for f in rules.scan_text(text)}


def test_roman_urdu_chest_pain_is_red():
    assert "chest_pain" in ids("mujhe seene mein dard ho raha hai")


def test_negated_chest_pain_not_flagged():
    assert "chest_pain" not in ids("nahi, chest pain nahi hai")
    assert "breathing_difficulty" not in ids("saans lene mein mushkil nahi")


def test_affirmation_after_nahi_still_flagged():
    assert "chest_pain" in ids("nahi theek nahi hoon, chest pain hai")


def test_fainting_is_watch_not_red():
    f = rules.scan_text("meri behen achanak behosh ho gayi thi")
    assert {x["id"]: x["level"] for x in f} == {"fainting": "yellow"}


def test_still_unconscious_is_red():
    assert "unresponsive" in ids("she is still unconscious")


def test_urdu_script_and_self_harm():
    assert "self_harm" in ids("میں خودکشی کرنا چاہتا ہوں")
    assert "chest_pain" in ids("میرے سینے میں درد ہے")


def test_seizure_and_stroke():
    assert "seizure" in ids("usay daura pada hai")
    assert "stroke_signs" in ids("chehra tedha ho gaya hai")


def test_measurement_extraction():
    m = rules.extract_measurements("mera bp 170/105 hai aur sugar 250 hai, bukhar 102")
    assert m["bp_sys"] == 170 and m["bp_dia"] == 105
    assert m["glucose_mgdl"] == 250
    assert 38 < m["temp_c"] < 40


def test_no_false_glucose_from_stray_number():
    m = rules.extract_measurements("mera sugar low lag raha hai 3 din se")
    assert "glucose_mgdl" not in m


def test_glucose_mmol_conversion():
    assert rules.canonicalize({"glucose": 3.0, "glucose_unit": "mmol/L"})["glucose_mgdl"] == 54


def test_glucose_levels():
    low = rules.risk_from_flags(rules.evaluate_measurements({"glucose_mgdl": 60}, True))
    vlow = rules.risk_from_flags(rules.evaluate_measurements({"glucose_mgdl": 48}, True))
    assert low == "yellow" and vlow == "red"


def test_bp_crisis_depends_on_symptoms():
    m = {"bp_sys": 190, "bp_dia": 125}
    assert rules.risk_from_flags(rules.evaluate_measurements(m, True)) == "red"
    assert rules.risk_from_flags(rules.evaluate_measurements(m, False)) == "yellow"


def test_newborn_fever_red():
    assert rules.risk_from_flags(rules.evaluate_measurements({"temp_c": 38.2}, True, "newborn")) == "red"


def test_audit_catches_dose_and_diagnosis():
    b = {"do_now": ["Take 500 mg now"], "relevant": "You have diabetes", "warning_signs": ["x"], "next_step": "see a doctor"}
    issues = rules.audit_bundle(b, "yellow")
    assert len(issues) >= 2


def test_audit_allows_do_not_stop_medicine():
    b = {"do_now": ["Do not stop your medicine"], "warning_signs": ["x"], "next_step": "see a doctor today"}
    assert rules.audit_bundle(b, "yellow") == []
