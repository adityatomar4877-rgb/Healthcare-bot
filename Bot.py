import streamlit as st
import pandas as pd
import openai
import random

# ------------------------------
# 1. Load FAQ CSV safely
# ------------------------------
try:
    faq_df = pd.read_csv("health_faq.csv")
except FileNotFoundError:
    st.error("❌ FAQ file not found. Please upload 'health_faq.csv' in the app directory.")
    st.stop()

# ------------------------------
# 2. FAQ Search Function (match disease names & symptoms)
# ------------------------------
def search_faq(user_input):
    user_input = user_input.lower()
    best_match = None
    best_score = 0

    for _, row in faq_df.iterrows():
        disease = str(row.get("Disease", "")).lower()
        symptoms = str(row.get("Common Symptoms", "")).lower()

        # Simple score: count keyword overlap
        score = sum(1 for word in user_input.split() if word in disease or word in symptoms)

        if score > best_score:
            best_score = score
            best_match = row

    if best_score > 0:
        # Build structured answer
        return f"""
**🦠 Disease:** {best_match.get('Disease', 'N/A')}

**Symptoms:** {best_match.get('Common Symptoms', 'N/A')}

**Notes:** {best_match.get('Notes', 'N/A')}

**Severity:** {best_match.get('Severity Tagging', 'N/A')}

**Preventions:** {best_match.get('Preventions', 'N/A')}

⚠️ {best_match.get('Disclaimers & Advice', 'N/A')}
"""
    return None

# ------------------------------
# 3. OpenAI Fallback Function (new API >=1.0.0)
# ------------------------------
def ask_openai(user_input):
    """Get response from OpenAI GPT if FAQ fails"""
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        return "⚠️ OpenAI API key not found. Add it in Streamlit Cloud → App → Settings → Secrets."

    openai.api_key = api_key

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful health awareness assistant. Never give prescriptions, only awareness and prevention info."},
                {"role": "user", "content": user_input}
            ],
            max_tokens=250
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"⚠️ Error while contacting OpenAI: {e}"

# ------------------------------
# 4. Streamlit UI
# ------------------------------
st.set_page_config(page_title="Healthcare Chatbot", page_icon="💊")
st.title("💊 Healthcare & Disease Awareness Chatbot")
st.write("Ask about diseases, symptoms, and prevention tips.")

# User input
user_question = st.text_input("Type your question here:")

if user_question:
    # Try FAQ first
    answer = search_faq(user_question)

    if answer:
        st.success(answer)
    else:
        with st.spinner("Fetching info from AI..."):
            answer = ask_openai(user_question)
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
