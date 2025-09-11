import streamlit as st
import pandas as pd
import random
import google.generativeai as genai
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
# 3. FAQ Search Function (Top 3 Matches)
# ------------------------------
def search_faq(user_input, top_n=3):
    user_input = user_input.lower()
    scores = []

    for _, row in faq_df.iterrows():
        disease = str(row.get("Disease", "")).lower()
        symptoms = str(row.get("Common Symptoms", "")).lower()
        score = sum(1 for word in user_input.split() if word in disease or word in symptoms)
        if score > 0:
            scores.append((score, row))

    scores = sorted(scores, key=lambda x: x[0], reverse=True)[:top_n]
    return [row for _, row in scores] if scores else None

# ------------------------------
# 4. Gemini Response Function (with Translation)
# ------------------------------
def ask_gemini(user_input, target_lang="en"):
    """Get response from Gemini in target language"""
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
# 5. Streamlit UI
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

# User input
user_question = st.text_input("Type your question here:")

# Auto-detect language
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
    # First try FAQ
    matches = search_faq(user_question)
    if matches:
        st.subheader("📋 Best Matches from Database:")
        for i, row in enumerate(matches, start=1):
            with st.container():
                st.markdown(f"### {i}. 🦠 {row.get('Disease', 'N/A')}")
                st.markdown(f"**Symptoms:** {row.get('Common Symptoms', 'N/A')}")
                st.markdown(f"**Notes:** {row.get('Notes', 'N/A')}")
                st.markdown(f"**Severity:** {row.get('Severity Tagging', 'N/A')}")
                st.info(f"⚠️ {row.get('Disclaimers & Advice', 'N/A')}")
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
    # Get translated tip via Gemini if not English
    if target_lang != "en":
        tip_text = ask_gemini(f"Translate this into {target_lang}: {random.choice(tips)}", target_lang)
        st.warning(tip_text)
    else:
        st.warning(random.choice(tips))
