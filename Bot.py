import streamlit as st
import pandas as pd
import random
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
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("⚠️ Gemini API key not found. Please add GEMINI_API_KEY in Streamlit Cloud → App → Settings → Secrets.")
    st.stop()

model = genai.GenerativeModel("gemini-1.5-flash")

# ------------------------------
# 3. FAQ Search Function (Top 3 Matches)
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
# 4. Gemini Fallback Function
# ------------------------------
def ask_gemini(user_input):
    """Get response from Gemini if FAQ fails"""
    try:
        response = model.generate_content(
            f"You are a helpful health awareness assistant. "
            f"Answer in the same language as the user. "
            f"Never give prescriptions, only awareness and prevention info.\n\nUser: {user_input}"
        )
        return response.text
    except Exception as e:
        return f"⚠️ Error while contacting Gemini: {e}"

# ------------------------------
# 5. Streamlit UI
# ------------------------------
st.set_page_config(page_title="Healthcare Chatbot", page_icon="💊")
st.title("💊 Healthcare & Disease Awareness Chatbot")
st.write("Ask about diseases, symptoms, and prevention tips in **any language** 🌍")

# User input
user_question = st.text_input("Type your question here:")

if user_question:
    # Step 1: Search FAQ
    matches = search_faq(user_question)

    if matches:
        st.subheader("📋 Best Matches from Database:")
        for i, row in enumerate(matches, start=1):
            answer = f"""
🦠 Disease: {row.get('Disease', 'N/A')}
📝 Symptoms: {row.get('Common Symptoms', 'N/A')}
📌 Notes: {row.get('Notes', 'N/A')}
⚠️ Severity: {row.get('Severity Tagging', 'N/A')}
💡 Advice: {row.get('Disclaimers & Advice', 'N/A')}
"""
            st.markdown(f"### {i}. \n{answer}")
            st.markdown("---")
    else:
        with st.spinner("Fetching info from Gemini..."):
            ai_answer = ask_gemini(user_question)
            st.success(ai_answer)

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

# SOS Button
st.markdown(
    """
    <a href="tel:108">
        <button style="background-color:red; color:white; padding:10px; border:none; border-radius:8px; font-size:16px;">
            🚨 SOS - Call 108
        </button>
    </a>
    """,
    unsafe_allow_html=True
)
