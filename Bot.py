import streamlit as st
import pandas as pd
import random
import google.generativeai as genai
from langdetect import detect
from difflib import SequenceMatcher

# ------------------------------
# 1. Load FAQ CSV safely
# ------------------------------
try:
    faq_df = pd.read_csv("health_faq.csv")
except FileNotFoundError:
    st.error("❌ FAQ file not found. Please upload 'health_faq.csv' in the app directory.")
    st.stop()

# ------------------------------
# 2. Configure Gemini
# ------------------------------
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    gemini_ready = True
except Exception:
    gemini_ready = False

# ------------------------------
# 2.1 Check Gemini Quota
# ------------------------------
def check_gemini_quota():
    if not gemini_ready:
        st.error("❌ Gemini API key missing. Add it in Streamlit Cloud → App → Settings → Secrets.")
        return
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Hello")
        st.success("✅ Gemini API key working — upgraded quota detected (not FreeTier).")
    except Exception as e:
        err = str(e)
        if "FreeTier" in err:
            st.error("⚠️ Your Gemini API key is still on FreeTier quota. Double-check that you used the student-plan key.")
        else:
            st.warning(f"⚠️ Gemini returned error: {err}")

check_gemini_quota()

# ------------------------------
# 3. Gemini Translation Functions
# ------------------------------
def translate_via_gemini(text, target_lang="en"):
    if not gemini_ready or target_lang == "en" or not text.strip():
        return text
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Translate the following text to {target_lang}:\n\n{text}")
        return response.text
    except Exception:
        return text

def to_english(text):
    if not gemini_ready or not text.strip():
        return text
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Translate this to English:\n\n{text}")
        return response.text
    except Exception:
        return text

# ------------------------------
# 4. FAQ Search Function
# ------------------------------
def search_faq(user_input, top_n=3):
    user_input = user_input.lower()
    scores = []
    for _, row in faq_df.iterrows():
        disease = str(row.get("Disease", "")).lower()
        symptoms = str(row.get("Common Symptoms", "")).lower()
        notes = str(row.get("Notes", "")).lower()

        score = max(
            SequenceMatcher(None, user_input, disease).ratio(),
            SequenceMatcher(None, user_input, symptoms).ratio(),
            SequenceMatcher(None, user_input, notes).ratio()
        )
        if score > 0.3:
            scores.append((score, row))

    scores = sorted(scores, key=lambda x: x[0], reverse=True)[:top_n]
    return [row for _, row in scores] if scores else None

# ------------------------------
# 5. Gemini Fallback
# ------------------------------
def ask_gemini(user_input, target_lang="en"):
    if not gemini_ready:
        return "⚠️ Gemini API key not found. Add it in Streamlit Cloud → App → Settings → Secrets."
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"You are a healthcare awareness assistant. "
            f"Answer in {target_lang}. Never give prescriptions, only awareness and prevention info.\n\n"
            f"Question: {user_input}"
        )
        return response.text
    except Exception as e:
        return f"⚠️ Error while contacting Gemini: {e}"

# ------------------------------
# 6. Streamlit UI
# ------------------------------
st.set_page_config(page_title="Healthcare Chatbot", page_icon="💊")
st.title("💊 Healthcare & Disease Awareness Chatbot")
st.write("Ask about diseases, symptoms, and prevention tips.")

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

if user_question.strip():
    try:
        detected_lang = detect(user_question)
        if detected_lang in lang_map.values() and detected_lang != target_lang:
            target_lang = detected_lang
            st.info(f"🌐 Auto-detected language switched to: {detected_lang.upper()}")
    except Exception:
        pass

submit = st.button("🔍 Search")

if submit and user_question:
    query_in_english = to_english(user_question)
    matches = search_faq(query_in_english)

    if matches:
        st.subheader("📋 Best Matches from Database:")
        for i, row in enumerate(matches, start=1):
            block = (
                f"Disease: {row.get('Disease','N/A')}\n"
                f"Symptoms: {row.get('Common Symptoms','N/A')}\n"
                f"Notes: {row.get('Notes','N/A')}\n"
                f"Severity: {row.get('Severity Tagging','N/A')}\n"
                f"Advice: {row.get('Disclaimers & Advice','N/A')}"
            )
            translated_block = translate_via_gemini(block, target_lang)
            st.info(translated_block)
            st.markdown("---")
    else:
        with st.spinner("Please Wait Patiently..."):
            answer = ask_gemini(user_question, target_lang)
            st.success(answer)

if st.button("💡 Show me a random health tip"):
    tips = [
        "Wash your hands regularly with soap and water.",
        "Drink at least 2–3 liters of clean water every day.",
        "Use mosquito nets to prevent vector-borne diseases.",
        "Eat fresh fruits and vegetables daily.",
        "Exercise at least 30 minutes every day."
    ]
    tip = random.choice(tips)
    if target_lang != "en":
        tip = translate_via_gemini(tip, target_lang)
    st.warning(tip)

if st.button("🆘 Emergency / SOS (Call 108)"):
    sos_message = (
        "🚨 If this is a medical emergency, please call **108** immediately "
        "or contact your nearest healthcare provider.\n\n"
        "[📞 Call 108](tel:108)"
    )
    if target_lang != "en":
        sos_message = translate_via_gemini(sos_message, target_lang)
    st.error(sos_message)
