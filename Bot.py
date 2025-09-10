import streamlit as st
import pandas as pd
import random
from rapidfuzz import fuzz
import google.generativeai as genai
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
import av

# ------------------------------
# 1. Load FAQ CSV safely
# ------------------------------
try:
    faq_df = pd.read_csv("health_faq.csv")
except FileNotFoundError:
    st.error("❌ FAQ file not found. Please upload 'health_faq.csv' in the app directory.")
    st.stop()

# ------------------------------
# 2. FAQ Search Function
# ------------------------------
def search_faq(user_input, top_n=3, min_score=70):
    """Search FAQ and return top N best matches only if score is good enough"""
    user_input = user_input.lower()
    scores = []

    for _, row in faq_df.iterrows():
        disease = str(row.get("Disease", "")).lower()
        symptoms = str(row.get("Common Symptoms", "")).lower()

        # fuzzy match against disease and symptoms
        score = max(
            fuzz.partial_ratio(user_input, disease),
            fuzz.partial_ratio(user_input, symptoms)
        )

        if score >= min_score:  # ✅ only keep relevant matches
            scores.append((score, row))

    scores = sorted(scores, key=lambda x: x[0], reverse=True)[:top_n]

    return [row for _, row in scores] if scores else None

# ------------------------------
# 3. Gemini Fallback Function
# ------------------------------
@st.cache_data
def ask_gemini(user_input):
    """Get response from Gemini if FAQ fails"""
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        return "⚠️ Gemini API key not found. Add it in Streamlit Cloud → App → Settings → Secrets."

    genai.configure(api_key=api_key)

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"You are a helpful health awareness assistant. "
            f"Never give prescriptions. Only share awareness, symptoms, and prevention info.\n\n"
            f"User question: {user_input}"
        )
        return response.text
    except Exception as e:
        return f"⚠️ Error while contacting Gemini: {e}"

# ------------------------------
# 4. Streamlit UI
# ------------------------------
st.set_page_config(page_title="Healthcare Chatbot", page_icon="💊")
st.title("💊 Healthcare & Disease Awareness Chatbot")
st.write("Ask about diseases, symptoms, and prevention tips.")

# User input
user_question = st.text_input("Type your question here:")
submit_btn = st.button("Submit")

# 🎤 Voice recognition via browser (streamlit-webrtc)
st.subheader("🎤 Speak Your Question")
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.frames = []

    def recv_audio(self, frame: av.AudioFrame) -> av.AudioFrame:
        self.frames.append(frame.to_ndarray().mean(axis=1))  # simple audio buffer
        return frame

webrtc_ctx = webrtc_streamer(
    key="speech-to-text",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
)

if webrtc_ctx.audio_receiver:
    st.info("🎙️ Recording... (stop to process)")
    # NOTE: For real speech-to-text, audio frames should be sent to Gemini or Google STT API.
    # Here we just acknowledge recording.
    st.warning("⚠️ Voice capture is working, but needs API hookup for speech-to-text.")

# Process only after Submit
if submit_btn and user_question:
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
        with st.spinner("Fetching info from Gemini..."):
            answer = ask_gemini(user_question)
            st.success(answer)

# 🔴 SOS Button
st.markdown("### 🚨 Emergency SOS")
if st.button("🔴 Call for Help"):
    st.error("🚨 Emergency Contacts")
    st.markdown("[🚑 Call Ambulance (108)](tel:108)", unsafe_allow_html=True)
    st.markdown("[🚓 Call Police (100)](tel:100)", unsafe_allow_html=True)
    st.markdown("[🚒 Call Fire (101)](tel:101)", unsafe_allow_html=True)

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
