"""Static strings in English (en), Urdu (ur) and Roman Urdu (roman_ur).
Emergency / fallback messages are static on purpose: no LLM or translation can distort them."""

LANGS = ("en", "ur", "roman_ur")

HEADINGS = {
    "en": {"understood": "What we understood", "relevant": "What could be relevant", "to_check": "What to check",
           "do_now": "What you can do now", "warning_signs": "Warning signs: get urgent help if",
           "next_step": "What to do next", "bring": "What to take to the doctor", "follow_up": "Follow-up"},
    "roman_ur": {"understood": "Hum ne kya samjha", "relevant": "Kya wajah ho sakti hai", "to_check": "Kya check karein",
                 "do_now": "Abhi aap kya kar sakte hain", "warning_signs": "Khatre ki alamaat: in mein se kuch ho to foran madad lein",
                 "next_step": "Agla qadam", "bring": "Doctor ke paas kya le jayein", "follow_up": "Follow-up"},
    "ur": {"understood": "ہم نے کیا سمجھا", "relevant": "کیا وجہ ہو سکتی ہے", "to_check": "کیا چیک کریں",
           "do_now": "ابھی آپ کیا کر سکتے ہیں", "warning_signs": "خطرے کی علامات: ان میں سے کچھ ہو تو فوراً مدد لیں",
           "next_step": "اگلا قدم", "bring": "ڈاکٹر کے پاس کیا لے جائیں", "follow_up": "فالو اپ"},
}

RISK_BANNER = {
    "green": {"en": "🟢 Lower concern", "roman_ur": "🟢 Kam khatra", "ur": "🟢 کم تشویش"},
    "yellow": {"en": "🟡 Needs medical evaluation", "roman_ur": "🟡 Doctor se check karwana zaroori hai", "ur": "🟡 ڈاکٹر سے معائنہ ضروری ہے"},
    "red": {"en": "🔴 Urgent", "roman_ur": "🔴 Fori madad zaroori", "ur": "🔴 فوری مدد ضروری"},
}

EMERGENCY = {
    "en": "🔴 **This may be an emergency.** Please get urgent medical help now. Call **{numbers}** or go to the nearest hospital emergency department immediately. Do not wait for more chat. If someone is with you, ask them to help you right now.",
    "roman_ur": "🔴 **Yeh emergency ho sakti hai.** Meharbani karke abhi foran tibbi madad lein. **{numbers}** par call karein ya qareeb tareen hospital ki emergency mein foran pohanchein. Is chat mein mazeed intezar na karein. Agar koi aap ke saath hai to usay abhi madad ke liye bulayein.",
    "ur": "🔴 **یہ ایمرجنسی ہو سکتی ہے۔** براہِ کرم ابھی فوری طبی مدد لیں۔ **{numbers}** پر کال کریں یا قریبی ہسپتال کی ایمرجنسی میں فوراً پہنچیں۔ اس چیٹ میں مزید انتظار نہ کریں۔ اگر کوئی آپ کے پاس ہے تو اسے ابھی مدد کے لیے بلائیں۔",
}

SELF_HARM = {
    "en": "💛 I'm really sorry you are feeling this much pain. You do not have to face it alone. Please tell someone you trust right now and stay with them. If you may act on these thoughts, call **{numbers}** or go to the nearest hospital emergency immediately.",
    "roman_ur": "💛 Mujhe afsos hai ke aap itni takleef mein hain. Aap akele nahi hain. Meharbani karke abhi kisi bharose ke insaan ko batayein aur unke saath rahein. Agar aap in khayalat par amal karne ka soch rahe hain to **{numbers}** par call karein ya foran qareeb ke hospital ki emergency mein jayein.",
    "ur": "💛 مجھے افسوس ہے کہ آپ اتنی تکلیف میں ہیں۔ آپ اکیلے نہیں ہیں۔ براہِ کرم ابھی کسی بھروسے کے شخص کو بتائیں اور ان کے ساتھ رہیں۔ اگر آپ ان خیالات پر عمل کرنے کا سوچ رہے ہیں تو **{numbers}** پر کال کریں یا فوراً قریبی ہسپتال کی ایمرجنسی میں جائیں۔",
}

# Short first-aid lines for specific emergency flags
FLAG_TIPS = {
    "unresponsive": {
        "en": "If the person is not responding but is breathing, lay them on their side and give nothing by mouth. If not breathing normally, start CPR if you know how.",
        "roman_ur": "Agar insaan jawab nahi de raha lekin saans le raha hai to usay karwat par litayein aur munh se kuch na dein. Agar saans normal nahi to CPR shuru karein (agar aati ho).",
        "ur": "اگر شخص جواب نہیں دے رہا مگر سانس لے رہا ہے تو اسے کروٹ پر لٹائیں اور منہ سے کچھ نہ دیں۔ اگر سانس نارمل نہیں تو سی پی آر شروع کریں (اگر آتی ہو)۔",
    },
    "seizure": {
        "en": "Move hard objects away, put nothing in the mouth, and turn the person on their side once the jerking stops. Note how long it lasted.",
        "roman_ur": "Sakht cheezein door karein, munh mein kuch na daalein, jhatke band hon to karwat par litayein. Dekhein kitni der raha.",
        "ur": "سخت چیزیں دور کریں، منہ میں کچھ نہ ڈالیں، جھٹکے رکنے پر کروٹ پر لٹائیں۔ دیکھیں کتنی دیر رہا۔",
    },
    "chest_pain": {
        "en": "Sit and rest, do not walk or drive yourself, and loosen tight clothing while help is on the way.",
        "roman_ur": "Baith kar aaram karein, khud chal kar ya gaari chala kar na jayein, tang kapray dheele karein.",
        "ur": "بیٹھ کر آرام کریں، خود چل کر یا گاڑی چلا کر نہ جائیں، تنگ کپڑے ڈھیلے کریں۔",
    },
    "severe_bleeding": {
        "en": "Press firmly on the wound with a clean cloth and keep pressing; do not remove soaked cloth, add more on top.",
        "roman_ur": "Zakhm par saaf kapray se mazbooti se dabao rakhein; bheega kapra na hatayein, uske upar aur kapra rakhein.",
        "ur": "زخم پر صاف کپڑے سے مضبوطی سے دباؤ رکھیں؛ بھیگا کپڑا نہ ہٹائیں، اس پر مزید کپڑا رکھیں۔",
    },
}

FALLBACK = {
    "en": "I could not prepare guidance that I am confident is safe for your situation. Please contact a healthcare professional or your nearest health facility today. If you have severe symptoms (trouble breathing, chest pain, fainting, confusion, seizure, heavy bleeding), call **{numbers}** now.",
    "roman_ur": "Main aap ki surat-e-haal ke liye aisi rehnumai tayyar nahi kar saka jis ke mehfooz hone par mujhe yaqeen ho. Meharbani karke aaj hi kisi healthcare professional ya qareebi sehat markaz se rabta karein. Agar shadeed alamaat hain (saans mein dikkat, seene mein dard, behoshi, uljhan, daura, ziyada khoon behna) to abhi **{numbers}** par call karein.",
    "ur": "میں آپ کی صورتِ حال کے لیے ایسی رہنمائی تیار نہیں کر سکا جس کے محفوظ ہونے پر مجھے یقین ہو۔ براہِ کرم آج ہی کسی ہیلتھ کیئر پروفیشنل یا قریبی صحت مرکز سے رابطہ کریں۔ اگر شدید علامات ہیں (سانس میں دشواری، سینے میں درد، بے ہوشی، الجھن، دورہ، زیادہ خون بہنا) تو ابھی **{numbers}** پر کال کریں۔",
}

CLARIFY_INTRO = {
    "en": "To guide you safely, I need a little more information:",
    "roman_ur": "Aap ko mehfooz rehnumai dene ke liye mujhe thori aur maloomat chahiye:",
    "ur": "آپ کو محفوظ رہنمائی دینے کے لیے مجھے تھوڑی اور معلومات چاہییں:",
}
CLARIFY_OUTRO = {
    "en": "You can answer in your own words, and \"don't know\" is fine.",
    "roman_ur": "Aap apne alfaaz mein jawab dein; \"pata nahi\" bhi theek hai.",
    "ur": "آپ اپنے الفاظ میں جواب دیں؛ \"پتا نہیں\" بھی ٹھیک ہے۔",
}

DISCLAIMER = {
    "en": "Sahaara AI gives early health information and care navigation. It does not diagnose and does not replace a doctor.",
    "roman_ur": "Sahaara AI shuru ki sehat ki maloomat aur rehnumai deta hai. Yeh tashkhees nahi karta aur doctor ka badal nahi hai.",
    "ur": "سہارا اے آئی ابتدائی صحت کی معلومات اور رہنمائی دیتا ہے۔ یہ تشخیص نہیں کرتا اور ڈاکٹر کا متبادل نہیں ہے۔",
}
