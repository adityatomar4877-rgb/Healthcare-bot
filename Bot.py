import streamlit as st
import pandas as pd
import random
import re
import string
from langdetect import detect
from difflib import SequenceMatcher

# ========== Basic page config ==========
st.set_page_config(page_title="Healthcare Chatbot", page_icon="💊")

# ========== Small helpers ==========
STOPWORDS = {
    "the","and","for","with","from","that","this","these","those","have","has","had",
    "been","was","were","are","is","a","an","in","on","at","by","of","to","or","as",
    "it","be","but","not","so","if","we","you","i","they","he","she","them","his","her"
}

MENTAL_HEALTH_KEYWORDS = {
    "sad","depressed","depression","anxious","anxiety","lonely","suicidal","suicide",
    "hopeless","down","stressed","stress","panic","afraid","scared","worthless",
    "want to die","kill myself","suicidal thoughts","suicidal ideation"
}

def clean_and_tokenize(text, min_len=3):
    """Lower, remove punctuation, return set of tokens length>=min_len, excluding stopwords."""
    if not text or not isinstance(text, str):
        return set()
    text = text.lower()
    text = re.sub(r"[{}]".format(re.escape(string.punctuation)), " ", text)
    tokens = [t.strip() for t in text.split() if t.strip()]
    tokens = [t for t in tokens if len(t) >= min_len and t not in STOPWORDS]
    return set(tokens)

def fuzzy_ratio(a, b):
    return SequenceMatcher(None, a or "", b or "").ratio()

def contains_mental_keyword(text):
    """Detect mental/emotional keywords in raw text (case-insensitive)."""
    if not text:
        return False
    s = text.lower()
    for kw in MENTAL_HEALTH_KEYWORDS:
        if kw in s:
            return True
    return False

# ========== 1. Load FAQ CSV safely ==========
try:
    faq_df = pd.read_csv("health_faq.csv")
except FileNotFoundError:
    st.error("❌ FAQ file not found. Please upload 'health_faq.csv' in the app directory.")
    st.stop()

# ========== 2. Configure Gemini (optional) ==========
genai = None
gemini_api_key = st.secrets.get("GEMINI_API_KEY", None)
gemini_ready = False
if gemini_api_key:
    try:
        import google.generativeai as genai_module
        genai_module.configure(api_key=gemini_api_key)
        genai = genai_module
        gemini_ready = True
    except Exception as e:
        st.warning(f"Gemini init failed: {e}")
else:
    st.info("Gemini API key not found in Streamlit secrets. Gemini functions will be disabled until you add GEMINI_API_KEY.")

# ========== 3. Gemini helpers ==========
def translate_via_gemini(text, target_lang="en"):
    if not gemini_ready or not text or target_lang == "en":
        return text
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(f"Translate the following text to {target_lang}:\n\n{text}")
        return resp.text if resp and getattr(resp, "text", None) else text
    except Exception:
        return text

def to_english(text):
    if not gemini_ready or not text:
        return text
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(f"Translate this to English:\n\n{text}")
        return resp.text if resp and getattr(resp, "text", None) else text
    except Exception:
        return text

def ask_gemini(user_input_en, target_lang="en"):
    if not gemini_ready:
        return "⚠️ Gemini AI not available. Please add GEMINI_API_KEY in Streamlit secrets to enable AI."
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            f"You are a healthcare awareness assistant. Answer the user's question in {target_lang}. "
            "Never give prescriptions; only provide awareness, prevention, and general guidance.\n\n"
            f"Question: {user_input_en}"
        )
        resp = model.generate_content(prompt)
        return resp.text if resp and getattr(resp, "text", None) else "⚠️ No response from Gemini."
    except Exception as e:
        return f"⚠️ Error while contacting Gemini: {e}"

# ========== 4. Improved FAQ Search ==========
def search_faq(user_input, top_n=3, fuzzy_threshold=0.60):
    """
    Return list of rows if strong match:
      - token overlap (after cleaning), OR
      - best fuzzy >= fuzzy_threshold
    Else return None so AI fallback triggers.
    """
    if not user_input or not isinstance(user_input, str):
        return None

    user_input_clean = user_input.strip()
    user_tokens = clean_and_tokenize(user_input_clean, min_len=3)
    candidates = []

    for _, row in faq_df.iterrows():
        disease = str(row.get("Disease", "") or "")
        symptoms = str(row.get("Common Symptoms", "") or "")
        notes = str(row.get("Notes", "") or "")
        combined = " ".join([disease, symptoms, notes]).strip()
        if not combined:
            continue

        row_tokens = clean_and_tokenize(combined, min_len=3)
        token_hits = len(user_tokens.intersection(row_tokens))
        score = fuzzy_ratio(user_input_clean.lower(), combined.lower())

        priority = score
        if token_hits > 0:
            priority = max(priority, 0.75 + min(0.20, token_hits * 0.05))

        candidates.append((priority, score, token_hits, row))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    top = candidates[:top_n]
    best_priority, best_fuzzy, best_token_hits, best_row = top[0]

    if best_token_hits > 0 or best_fuzzy >= fuzzy_threshold:
        return [c[3] for c in top]

    return None

# ========== 5. UI ==========
st.title("💊 Healthcare & Disease Awareness Chatbot")
st.write("Ask about diseases, symptoms, prevention. Database checked first; AI fallback only if needed.")

lang_map = {
    "English": "en",
    "हिंदी (Hindi)": "hi",
    "தமிழ் (Tamil)": "ta",
    "বাংলা (Bengali)": "bn",
    "ગુજરાતી (Gujarati)": "gu",
    "मराठी (Marathi)": "mr",
    "తెలుగు (Telugu)": "te",
    "ಕನ್ನಡ (Kannada)": "kn",
    "മലയാളം (Malayalam)": "ml",
    "ਪੰਜਾਬੀ (Punjabi)": "pa",
    "اردو (Urdu)": "ur",
    "ଓଡ଼ିଆ (Odia)": "or"
}

language_choice = st.selectbox("🌐 Choose Language:", list(lang_map.keys()))
target_lang = lang_map[language_choice]

user_question = st.text_input("Type your question here:")

force_ai = st.checkbox("🤖 Ask AI Directly (skip database)")

if user_question.strip():
    try:
        detected_lang = detect(user_question)
        if detected_lang in lang_map.values() and detected_lang != target_lang:
            st.info(f"🌐 Auto-detected language: {detected_lang.upper()} (results will be displayed in selected language)")
    except Exception:
        pass

# ========== 6. Submit logic with mental-health guard ==========
submit = st.button("🔍 Search")
if submit and user_question:
    if contains_mental_keyword(user_question):
        st.warning("It looks like you're describing feelings or emotional distress. Showing supportive guidance (AI) rather than database disease matches.")
        query_in_english = to_english(user_question) if gemini_ready else user_question
        with st.spinner("🤖 Consulting AI for supportive guidance..."):
            answer_en = ask_gemini(query_in_english, "en")
            answer_final = translate_via_gemini(answer_en, target_lang)
            st.success(answer_final)
            if any(k in user_question.lower() for k in ("suicide","suicidal","want to die","kill myself")):
                st.error("If you are in immediate danger or thinking of harming yourself, please contact local emergency services immediately.")
        st.stop()

    query_in_english = to_english(user_question) if gemini_ready else user_question

    if force_ai:
        with st.spinner("🤖 Asking Gemini AI..."):
            answer_en = ask_gemini(query_in_english, "en")
            answer_final = translate_via_gemini(answer_en, target_lang)
            st.success(answer_final)
    else:
        matches = search_faq(query_in_english, top_n=3, fuzzy_threshold=0.60)
        if matches:
            st.subheader("📋 Best Matches from Database:")
            for row in matches:
                block = (
                    f"**Disease:** {row.get('Disease','N/A')}\n\n"
                    f"**Symptoms:** {row.get('Common Symptoms','N/A')}\n\n"
                    f"**Notes:** {row.get('Notes','N/A')}\n\n"
                    f"**Severity:** {row.get('Severity Tagging','N/A')}\n\n"
                    f"**Advice:** {row.get('Disclaimers & Advice','N/A')}"
                )
                displayed = translate_via_gemini(block, target_lang) if target_lang != "en" else block
                st.info(displayed)
                st.markdown("---")
        else:
            with st.spinner("🤖 No useful DB match, asking Gemini AI..."):
                answer_en = ask_gemini(query_in_english, "en")
                answer_final = translate_via_gemini(answer_en, target_lang)
                st.success(answer_final)

# ========== 7. Extras ==========
if st.button("💡 Show me a random health tip"):
    tips = [
        "Wash your hands regularly with soap and water.",
        "Drink at least 2–3 liters of clean water every day.",
        "Use mosquito nets to prevent vector-borne diseases.",
        "Eat fresh fruits and vegetables daily.",
        "Exercise at least 30 minutes every day."
    ]
    tip = random.choice(tips)
    tip = translate_via_gemini(tip, target_lang)
    st.warning(tip)

if st.button("🆘 Emergency / SOS (Call 108)"):
    sos_message = (
        "🚨 If this is a medical emergency, please call **108** immediately "
        "or contact your nearest healthcare provider.\n\n"
        "[📞 Call 108](tel:108)"
    )
    sos_message = translate_via_gemini(sos_message, target_lang)
    st.error(sos_message)
