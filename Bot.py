import streamlit as st
import pandas as pd
import random
import google.generativeai as genai
from googletrans import Translator
from langdetect import detect

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
# 3. Translator Setup
# ------------------------------
translator = Translator()

def translate_text(text, target_lang):
    """Translate text to target language"""
    if not text or target_lang == "en":
        return text
    try:
        return translator.translate(text, dest=target_lang).text
    except Exception:
        return text  # fallback to English if translation fails

# ------------------------------
# 4. FAQ Search Function (Top 3 Matches)
# ------------------------------
def search_faq(user_input, top_n=3):
    """Search FAQ and return top N best matches"""
    user_input = user_input.lower()
    scores = []

    for _, row in faq_df.iterrows():
        disease = str(row.get("Disease", "")).lower()
        symptoms = str(row.get("Common Symptoms", "")).lower()

        # Score = keyword overlap
        score = sum(1 for word in user_input.split() if word in disease or word in symptoms)

        if score > 0:  # Only consider relevant rows
            scores.append((score, row))

    # Sort by score (highest first) and pick top N
    scores = sorted(scores, key=lambda x: x[0], reverse=True)[:top_n]

    return [row for _, row in scores] if scores else None

# ------------------------------
# 5. Gemini Fallback Function
# ------------------------------
def ask_gemini(user_input, target_lang="en"):
    """Get response from Gemini"""
    if not gemini_ready:
        return "⚠️ Gemini API key not found. Add it in Streamlit Cloud → App → Settings → Secrets."

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"Answer in {target_lang}. You are a health awareness assistant. "
            f"Never give prescriptions, only awareness and prevention info.\n\nQuestion: {user_input}"
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

# Language map
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

# Manual language selection
language_choice = st.selectbox("🌐 Choose Language:", list(lang_map.keys()))
target_lang = lang_map[language_choice]

# User input + Enter button
user_question = st.text_input("Type your question here:")

# Auto-detect language if user typed something
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
    # Try FAQ first
    matches = search_faq(user_question)

    if matches:
        st.subheader("📋 Best Matches from Database:")
        for i, row in enumerate(matches, start=1):
            with st.container():
                st.markdown(f"### {i}. 🦠 {translate_text(row.get('Disease', 'N/A'), target_lang)}")
                st.markdown(f"**Symptoms:** {translate_text(row.get('Common Symptoms', 'N/A'), target_lang)}")
                st.markdown(f"**Notes:** {translate_text(row.get('Notes', 'N/A'), target_lang)}")
                st.markdown(f"**Severity:** {translate_text(row.get('Severity Tagging', 'N/A'), target_lang)}")
                st.info(f"⚠️ {translate_text(row.get('Disclaimers & Advice', 'N/A'), target_lang)}")
                st.markdown("---")
    else:
        with st.spinner("Please Wait Patiently..."):
            answer = ask_gemini(user_question, target_lang)
            st.success(answer)

# Random health tip
if st.button("💡 Show me a random health tip"):
    tips = [
        "Wash your hands regularly with soap and water.",
        "Drink at least 2–3 liters of clean water every day.",
        "Use mosquito nets to prevent vector-borne diseases.",
        "Eat fresh fruits and vegetables daily.",
        "Exercise at least 30 minutes every day."
    ]
    st.warning(translate_text(random.choice(tips), target_lang))
