import streamlit as st
import pandas as pd
import openai
import os
import random
import re

# ------------------------------
# 1. Load your FAQ data (CSV)
# ------------------------------
faq_df = pd.read_csv("health_faq.csv")

# Clean column names
faq_df.columns = faq_df.columns.str.strip()

# ------------------------------
# 2. Functions
# ------------------------------
def highlight_keywords(text, keywords):
    """Highlight matched keywords in the text using Markdown bold"""
    for word in keywords:
        pattern = re.compile(rf"\\b{re.escape(word)}\\b", re.IGNORECASE)
        text = pattern.sub(f"**{word}**", text)
    return text


def search_faq(user_input):
    """Search for matching Diseases or Symptoms in the CSV file, return multiple matches with highlights"""
    user_words = user_input.lower().split()
    matches_found = []

    for _, row in faq_df.iterrows():
        # Combine disease and symptoms as searchable text
        searchable_text = str(row['Disease']).lower() + " " + str(row['Common Symptoms']).lower()
        matches = sum(1 for word in user_words if word in searchable_text)

        if matches > 0:
            # Build a helpful answer from CSV fields
            answer = f"**Disease:** {row['Disease']}\n\n" \
                     f"**Common Symptoms:** {row['Common Symptoms']}\n\n" \
                     f"**Notes:** {row['Notes']}\n\n" \
                     f"**Severity:** {row['Severity Tagging']}\n\n" \
                     f"**Advice:** {row['Disclaimers & Advice']}"
            # Highlight keywords
            answer = highlight_keywords(answer, user_words)
            matches_found.append((matches, answer))

    # Sort by number of matches (descending)
    matches_found.sort(key=lambda x: x[0], reverse=True)

    if matches_found:
        return "\n\n---\n\n".join([m[1] for m in matches_found[:3]])  # return top 3 matches
    return None


def ask_openai(user_input):
    """Fallback to OpenAI GPT if no FAQ matches"""
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        return "⚠️ OpenAI API key not found. Please add it to .streamlit/secrets.toml"

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
