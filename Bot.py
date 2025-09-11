import streamlit as st
import pandas as pd
import random
import os
import google.generativeai as genai

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
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ------------------------------
# 3. FAQ Search Function
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
# 4. Gemini Fallback Function
# ------------------------------
def ask_gemini(user_input):
    if not GEMINI_API_KEY:
        return "⚠️ Gemini API key not found. Add it in Streamlit Cloud → App → Settings → Secrets."

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"You are a helpful health awareness assistant. "
            f"Only provide awareness, symptoms, and prevention info. No prescriptions.\n\n"
            f"User: {user_input}"
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

# Hidden text area for capturing voice input
voice_input = st.text_area("Voice Capture", "", key="voice_input", label_visibility="collapsed")

# JavaScript for speech recognition
st.markdown(
    """
    <script>
    function startListening() {
        if (!('webkitSpeechRecognition' in window)) {
            alert("⚠️ Your browser does not support Speech Recognition.");
            return;
        }
        var recognition = new webkitSpeechRecognition();
        recognition.lang = "en-US";
        recognition.start();
        recognition.onresult = function(event) {
            var transcript = event.results[0][0].transcript;
            var textarea = window.parent.document.querySelector('textarea[data-testid="stTextArea"]');
            if (textarea) {
                textarea.value = transcript;
                textarea.dispatchEvent(new Event('input', { bubbles: true }));
            }
        };
    }
    </script>
    """,
    unsafe_allow_html=True
)

# Input field + Voice button
col1, col2 = st.columns([4, 1])
with col1:
    user_question = st.text_input("Type your question here:", value=voice_input)
with col2:
    st.markdown('<button onclick="startListening()" style="margin-top:25px;">🎤</button>', unsafe_allow_html=True)

# Submit button
if st.button("Ask"):
    if user_question:
        with st.spinner("⏳ Fetching info..."):
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
                answer = ask_gemini(user_question)
                st.subheader("🤖 AI Response")
                st.write(answer)

# Random health tip
if st.button("💡 Show me a random health tip"):
    tips = [
        "Wash your hands regularly with soap and water.",
        "Drink at least 2–3 liters of clean water every day.",
        "Use mosquito nets to prevent vector-borne diseases.",
        "Eat fresh fruits and vegetables daily.",
        "Exercise at least 30 minutes every day."
    ]
    st.warning(random.choice(tips))

# SOS Button → Phone Dialer (changed to 108 🚨)
st.markdown(
    """
    <a href="tel:108">
        <button style="background-color:red;color:white;padding:15px 30px;border:none;border-radius:10px;font-size:18px;margin-top:20px;">
            🚨 SOS
        </button>
    </a>
    """,
    unsafe_allow_html=True
)
