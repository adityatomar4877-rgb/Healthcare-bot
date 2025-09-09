import streamlit as st
import pandas as pd
import random
from openai import OpenAI
from rapidfuzz import fuzz
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
import queue
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

        score = fuzz.partial_ratio(user_input, disease) + fuzz.partial_ratio(user_input, symptoms)

        if score > 0:
            scores.append((score, row))

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
# 4. Voice Input Setup
# ------------------------------
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_queue = queue.Queue()

    def recv_audio(self, frame):
        audio_data = frame.to_ndarray().tobytes()
        self.audio_queue.put(audio_data)
        return frame

# ------------------------------
# 5. Streamlit UI
# ------------------------------
st.set_page_config(page_title="Healthcare Chatbot", page_icon="💊")
st.title("💊 Healthcare & Disease Awareness Chatbot")
st.write("Ask about diseases, symptoms, and awareness tips.")

# Text input with Enter button
user_question = st.text_input("Type your question here:")
if st.button("Submit"):
    if user_question:
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

# Voice Input
st.subheader("🎤 Voice Input")
webrtc_ctx = webrtc_streamer(
    key="speech-to-text",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
)

if st.button("Transcribe Voice"):
    if webrtc_ctx and webrtc_ctx.audio_processor:
        recognizer = sr.Recognizer()
        audio_bytes = b''.join(list(webrtc_ctx.audio_processor.audio_queue.queue))
        try:
            audio_data = sr.AudioData(audio_bytes, 16000, 2)
            text = recognizer.recognize_google(audio_data)
            st.success(f"🗣️ You said: {text}")

            matches = search_faq(text)
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
                    answer = ask_openai(text)
                    st.success(answer)
        except Exception as e:
            st.error(f"⚠️ Could not transcribe: {e}")

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
