import streamlit as st
import pandas as pd
import random
from openai import OpenAI
import speech_recognition as sr

# ------------------------------
# 1. Load FAQ CSV safely
# ------------------------------
try:
    faq_df = pd.read_csv("health_faq.csv")
except FileNotFoundError:
    st.error("❌ FAQ file not found. Please upload 'health_faq.csv' in the app directory.")
    st.stop()

# ------------------------------
# 2. FAQ Search Function (Top 3 Matches)
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
# 3. OpenAI Fallback Function
# ------------------------------
def ask_openai(user_input):
    """Get response from OpenAI GPT if FAQ fails"""
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        return "⚠️ OpenAI API key not found. Add it in Streamlit Cloud → App → Settings → Secrets."

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful health awareness assistant. Never give prescriptions, only awareness and prevention info."},
                {"role": "user", "content": user_input}
            ],
            max_tokens=250
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Error while contacting OpenAI: {e}"

# ------------------------------
# 4. Voice Recognition Function
# ------------------------------
def recognize_speech():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎤 Listening... please speak now.")
        audio = r.listen(source, phrase_time_limit=5)
    try:
        text = r.recognize_google(audio)
        st.success(f"✅ You said: {text}")
        return text
    except sr.UnknownValueError:
        st.error("❌ Sorry, could not understand your voice.")
    except sr.RequestError:
        st.error("⚠️ Could not connect to speech recognition service.")
    return None

# ------------------------------
# 5. Streamlit UI
# ------------------------------
st.set_page_config(page_title="Healthcare Chatbot", page_icon="💊")
st.title("💊 Healthcare & Disease Awareness Chatbot")
st.write("Ask about diseases, symptoms, and prevention tips.")

# Text input field
user_question = st.text_input("Type your question here:")

# Buttons: Enter + Voice
col1, col2 = st.columns([1, 1])
with col1:
    enter_pressed = st.button("➡ Enter")
with col2:
    voice_pressed = st.button("🎤 Speak")

# Handle input if Enter button pressed
if enter_pressed and user_question:
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
        with st.spinner("Fetching info from AI..."):
            answer = ask_openai(user_question)
            st.success(answer)

# Handle voice input if Voice button pressed
if voice_pressed:
    spoken_text = recognize_speech()
    if spoken_text:
        matches = search_faq(spoken_text)
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
            with st.spinner("Fetching info from AI..."):
                answer = ask_openai(spoken_text)
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
    st.warning(random.choice(tips))
