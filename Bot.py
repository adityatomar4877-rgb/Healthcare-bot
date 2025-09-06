import streamlit as st
import pandas as pd
import openai
import random
import re
import os

# ------------------------------
# 1. Load your FAQ data (CSV)
# ------------------------------
faq_df = pd.read_csv("health_faq.csv")

# ------------------------------
# 2. Helper: Tokenizer for clean word matching
# ------------------------------
STOPWORDS = {"and","or","the","a","an","to","of","in","on","with","for","is","are"}

def tokenize(text: str):
    """Turn text into clean, comparable words"""
    words = re.findall(r"[a-z0-9]+", str(text).lower())
    return [w for w in words if w not in STOPWORDS]

# ------------------------------
# 3. Functions
# ------------------------------
def search_faq(user_input):
    """Search for matching disease/symptoms in the CSV file"""
    user_words = tokenize(user_input)
    best_match = None
    max_matches = 0

    for _, row in faq_df.iterrows():
        disease_words = tokenize(row.get("Disease", ""))
        symptom_words = tokenize(row.get("Common Symptoms", ""))
        all_words = disease_words + symptom_words

        matches = sum(1 for word in user_words if word in all_words)

        if matches > max_matches:
            max_matches = matches
            best_match = (
                f"🦠 **Disease:** {row.get('Disease','N/A')}\n\n"
                f"🤒 **Common Symptoms:** {row.get('Common Symptoms','N/A')}\n\n"
                f"📝 **Notes:** {row.get('Notes','N/A')}\n\n"
                f"⚠️ **Severity:** {row.get('Severity Tagging','N/A')}\n\n"
                f"💡 **Advice:** {row.get('Disclaimers & Advice','N/A')}"
            )

    if max_matches > 0:
        return best_match
    return None


def ask_openai(user_input):
    """Fallback to OpenAI GPT if no FAQ matches"""
    api_key = os.getenv("OPENAI_API_KEY")  # safer than hardcoding
    if not api_key:
        return "⚠️ No AI key available. Please rely on the FAQ answers for now."

    openai.api_key = "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"

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
        return f"⚠️ AI lookup failed: {e}"

# ------------------------------
# 4. Streamlit User Interface
# ------------------------------
st.set_page_config(page_title="Healthcare Chatbot", page_icon="💊")
st.title("💊 Healthcare & Disease Awareness Chatbot")
st.write("Ask me about common diseases, symptoms, and prevention tips.")

# User input
user_question = st.text_input("Type your question here:")

if user_question:
    answer = search_faq(user_question)  # CSV lookup first
    if answer:
        st.markdown(answer)             # render Markdown (better than success box)
    else:
        st.info("Fetching information from AI...")
        answer = ask_openai(user_question)
        st.markdown(answer)

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
