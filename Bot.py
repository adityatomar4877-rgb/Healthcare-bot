import streamlit as st
import pandas as pd
import random
from langdetect import detect
from difflib import SequenceMatcher

# ========== 1. Load FAQ CSV safely ==========
try:
    faq_df = pd.read_csv("health_faq.csv")
except FileNotFoundError:
    st.error("❌ FAQ file not found. Please upload 'health_faq.csv' in the app directory.")
    st.stop()

# ========== 2. Configure Gemini ==========
gemini_api_key = st.secrets.get("GEMINI_API_KEY", None)
gemini_ready = False
if gemini_api_key:
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_api_key)
        gemini_ready = True
    except Exception as e:
        st.error(f"Gemini API could not be initialized: {e}")
else:
    st.warning("⚠️ Gemini API key not found in Streamlit secrets. Add GEMINI_API_KEY.")

# ========== 3. Translation Helpers ==========
def translate_via_gemini(text, target_lang="en"):
    """Translate given text into target language using Gemini."""
    if not gemini_ready or target_lang == "en" or not text.strip():
        return text
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Translate the following text to {target_lang}:\n\n{text}")
        return response.text if response and response.text else text
    except Exception as e:
        st.error(f"Translation error with Gemini: {e}")
        return text

def to_english(text):
    """Convert any text to English using Gemini."""
    if not gemini_ready or not text.strip():
        return text
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(f"Translate this to English:\n\n{text}")
        return response.text if response and response.text else text
    except Exception as e:
        st.error(f"English translation error with Gemini: {e}")
        return text

# ========== 4. FAQ Search Function ==========
def search_faq(user_input, top_n=3):
    """Search FAQ database with keyword + fuzzy logic."""
    user_input = user_input.lower().strip()
    scores = []
    found_exact = False

    for _, row in faq_df.iterrows():
        disease = str(row.get("Disease", "")).lower()
        symptoms = str(row.get("Common Symptoms", "")).lower()
        notes = str(row.get("Notes", "")).lower()

        # Check direct keyword presence
        if any(word in user_input for word in (disease.split() + symptoms.split() + notes.split())):
            found_exact = True

        # Fuzzy similarity
        score = max(
            SequenceMatcher(None, user_input, disease).ratio(),
            SequenceMatcher(None, user_input, symptoms).ratio(),
            SequenceMatcher(None, user_input, notes).ratio()
        )

        if score >= 0.3:  # relaxed threshold
            scores.append((score, row))

    scores = sorted(scores, key=lambda x: x[0], reverse=True)[:top_n]

    # Always return if exact keyword match
    if found_exact and scores:
        return [row for _, row in scores]

    return [row for _, row in scores] if scores else None

# ========== 5. Gemini Fallback ==========
def ask_gemini(user_input_en, target_lang="en"):
    if not gemini_ready:
        st.warning("⚠️ Gemini unavailable. Add API key in Streamlit secrets.")
        return "⚠️ Gemini AI not available. Please contact admin."
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"You are a healthcare awareness assistant. "
            f"Answer in {target_lang}. Never give prescriptions, only awareness and prevention info.\n\n"
            f"Question: {user_input_en}"
        )
        return response.text if response and response.text else "⚠️ No response from Gemini."
    except Exception as e:
        st.error(f"Gemini error: {e}")
        return f"⚠️ Error while contacting Gemini: {e}"

# ========== 6. Streamlit UI ==========
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
    except Exception as e:
        st.warning(f"Language detection error: {e}")

# Toggle for forcing AI
force_ai = st.checkbox("💬 Ask AI Directly (skip database search)")

submit = st.button("🔍 Search")
if submit and user_question:
    query_in_english = to_english(user_question)

    if force_ai:
        # Direct AI mode
        with st.spinner("🤖 Asking Gemini AI..."):
            answer_en = ask_gemini(query_in_english, "en")
            answer_final = translate_via_gemini(answer_en, target_lang)
            st.success(answer_final)
    else:
        matches = search_faq(query_in_english)
        if matches:
            st.subheader("📋 Best Matches from Database:")
            for row in matches:
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
            with st.spinner("🤖 Consulting your problem..."):
                answer_en = ask_gemini(query_in_english, "en")
                answer_final = translate_via_gemini(answer_en, target_lang)
                st.success(answer_final)

# ========== 7. Random Health Tip ==========
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

# ========== 8. SOS / Emergency Button ==========
if st.button("🆘 Emergency / SOS (Call 108)"):
    sos_message = (
        "🚨 If this is a medical emergency, please call **108** immediately "
        "or contact your nearest healthcare provider.\n\n"
        "[📞 Call 108](tel:108)"
    )
    sos_message = translate_via_gemini(sos_message, target_lang)
    st.error(sos_message)
