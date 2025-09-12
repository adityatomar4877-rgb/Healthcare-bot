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
# 3. Helper Functions
# ------------------------------
def safe_get(row, col):
    """Safely fetch column value from row"""
    return str(row[col]) if col in row and pd.notna(row[col]) else "N/A"

def translate_via_gemini(text, target_lang="en"):
    """Translate text safely with Gemini"""
    if not gemini_ready or target_lang == "en" or not text.strip():
        return text
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Translate the following text to {target_lang}:\n\n{text}")
        return response.text if response and response.text else text
    except Exception:
        return text

def to_english(text):
    """Translate user query to English for searching"""
    if not gemini_ready or not text.strip():
        return text
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Translate this to English:\n\n{text}")
        return response.text if response and response.text else text
    except Exception:
        return text

def search_faq(user_input, top_n=3):
    """Search FAQ using fuzzy string similarity"""
    user_input = user_input.lower()
    scores = []

    for _, row in faq_df.iterrows():
        disease = safe_get(row, "Disease").lower()
        symptoms = safe_get(row, "Common Symptoms").lower()
        notes = safe_get(row, "Notes").lower()

        score = max(
            SequenceMatcher(None, user_input, disease).ratio(),
            SequenceMatcher(None, user_input, symptoms).ratio(),
            SequenceMatcher(None, user_input, notes).ratio()
        )

        if score > 0.3:
            scores.append((score, row))

    scores = sorted(scores, key=lambda x: x[0], reverse=True)[:top_n]
    return [row for _, row in scores] if scores else None

def ask_gemini(user_input, target_lang="en"):
    """Fallback Gemini response"""
    if not gemini_ready:
        return "⚠️ Gemini API key not found. Add it in Streamlit Cloud → App → Settings → Secrets."
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"You are a healthcare awareness assistant. "
            f"Answer in {target_lang}. Never give prescriptions, only awareness and prevention info.\n\n"
            f"Question: {user_input}"
        )
        return response.text if response and response.text else "⚠️ No response from Gemini."
    except Exception as e:
        return f"⚠️ Error while contacting Gemini: {e}"

# ------------------------------
# 4. Streamlit UI
# ------------------------------
st.set_page_config(page_title="Healthcare Chatbot", page_icon="💊")
st.title("💊 Healthcare & Disease Awareness Chatbot")
st.write("Ask about diseases, symptoms, and prevention tips.")

# Supported Languages
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

# Language selection
language_choice = st.selectbox("🌐 Choose Language:", list(lang_map.keys()))
target_lang = lang_map[language_choice]

# User input
user_question = st.text_input("Type your question here:")
submit = st.button("🔍 Search")

# Auto-detect language
if user_question.strip():
    try:
        detected_lang = detect(user_question)
        if detected_lang in lang_map.values() and detected_lang != target_lang:
            target_lang = detected_lang
            st.info(f"🌐 Auto-detected language switched to: {detected_lang.upper()}")
    except Exception:
        pass

# ------------------------------
# 5. Handle Query
# ------------------------------
if submit and user_question:
    query_in_english = to_english(user_question)

    matches = search_faq(query_in_english)

    if matches:
        st.subheader("📋 Best Matches from Database:")
        for i, row in enumerate(matches, start=1):
            block = (
                f"Disease: {safe_get(row,'Disease')}\n"
                f"Symptoms: {safe_get(row,'Common Symptoms')}\n"
                f"Notes: {safe_get(row,'Notes')}\n"
                f"Severity: {safe_get(row,'Severity Tagging')}\n"
                f"Advice: {safe_get(row,'Disclaimers & Advice')}"
            )
            translated_block = translate_via_gemini(block, target_lang)
            st.info(translated_block)
            st.markdown("---")
    else:
        with st.spinner("Please Wait Patiently..."):
            answer = ask_gemini(user_question, target_lang)
            st.success(answer)

# ------------------------------
# 6. Random Health Tip
# ------------------------------
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

# ------------------------------
# 7. SOS / Emergency Button
# ------------------------------
if st.button("🆘 Emergency / SOS (Call 108)"):
    sos_message = (
        "🚨 If this is a medical emergency, please call **108** immediately "
        "or contact your nearest healthcare provider.\n\n"
        "[📞 Call 108](tel:108)"
    )
    if target_lang != "en":
        sos_message = translate_via_gemini(sos_message, target_lang)
    st.error(sos_message)
