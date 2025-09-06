import streamlit as st
import pandas as pd
import openai
import random

# ------------------------------
# 1. Load your FAQ data (CSV)
# ------------------------------
faq_df = pd.read_csv("health_faq.csv")

# ------------------------------
# 2. Functions
# ------------------------------

def search_faq(user_input):
    """Search for matching FAQ keywords in the CSV file"""
    user_words = user_input.lower().split()
    best_match = None
    max_matches = 0

    for _, row in faq_df.iterrows():
        if "question" not in row or "answer" not in row:
            continue
        question_words = str(row["question"]).lower().split()
        matches = sum(1 for word in user_words if word in question_words)

        if matches > max_matches:
            max_matches = matches
            best_match = row["answer"]

    if max_matches > 0:
        return best_match
    return None


def ask_openai(user_input):
    """Fallback to OpenAI GPT if no FAQ matches"""
    try:
        api_key = st.secrets["OPENAI_API_KEY"]  # ✅ Cloud-safe secrets
    except Exception:
        return "⚠️ OpenAI API key not found. Please add it in Streamlit Cloud → App → Settings → Secrets."

    openai.api_key = api_key

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful health awareness assistant. Never give prescriptions, only awareness and prevention info."},
                {"role": "user", "content": user_input}
            ],
            max_tokens=200
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"⚠️ Error while contacting OpenAI: {e}"


# ------------------------------
# 3. Streamlit User Interface
# ------------------------------
st.set_page_config(page_title="Healthcare Chatbot", page_icon="💊")
st.title("💊 Healthcare & Disease Awareness Chatbot")
st.write("Ask me about common diseases, symptoms, and prevention tips.")

# User input
user_question = st.text_input("Type your question here:")

if user_question:
    # First: Try to answer from FAQ
    answer = search_faq(user_question)

    # If no FAQ answer, use OpenAI
    if answer:
        st.success(answer)
    else:
        st.info("Fetching information from AI...")
        answer = ask_openai(user_question)
        st.success(answer)

# Extra: Show a health tip
if st.button("💡 Show me a random health tip"):
    tips = [
        "Wash your hands regularly with soap and water.",
        "Drink at least 2–3 liters of clean water every day.",
        "Use mosquito nets to prevent vector-borne diseases.",
        "Eat fresh fruits and vegetables daily.",
        "Exercise at least 30 minutes every day."
    ]
    st.warning(random.choice(tips))
