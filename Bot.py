import streamlit as st
import pandas as pd
import openai
import random
import difflib

# ------------------------------
# 1. Load CSV safely
# ------------------------------
try:
    faq_df = pd.read_csv("health_faq.csv")
    # Normalize column names
    faq_df.columns = faq_df.columns.str.strip().str.lower()
except FileNotFoundError:
    st.error("❌ FAQ file not found. Please upload 'health_faq.csv' in the app directory.")
    st.stop()

# ------------------------------
# 2. Search Function
# ------------------------------
def search_disease(user_input):
    """Find best matching diseases and return details"""
    diseases = faq_df["disease"].dropna().tolist()

    # Get best 3 close matches
    best_matches = difflib.get_close_matches(user_input, diseases, n=3, cutoff=0.4)

    results = []
    for match in best_matches:
        row = faq_df[faq_df["disease"] == match].iloc[0]

        result = f"""
### 🦠 Disease: {row['disease']}
**Symptoms:** {row.get('common symptoms', 'Not available')}

**Preventions:**  
{row.get('preventions', 'Not available')}

**Notes:** {row.get('notes', 'Not available')}
**Severity:** {row.get('severity tagging', 'Not available')}
**Disclaimer:** {row.get('disclaimers & advice', 'Not available')}
        """
        results.append(result)

    return results

# ------------------------------
# 3. OpenAI Fallback Function
# ------------------------------
def ask_openai(user_input):
    """Get response from OpenAI GPT if FAQ fails (new API)"""
    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        return "⚠️ OpenAI API key not found. Add it in Streamlit Cloud → App → Settings → Secrets."

    client = openai.OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful health awareness assistant. Always include prevention tips in your response. Never give prescriptions."},
                {"role": "user", "content": user_input}
            ],
            max_tokens=250
        )
        return response.choices[0].message.content
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
    # Search in CSV first
    results = search_disease(user_question)

    if results:
        for res in results:
            st.success(res)
    else:
        # Fallback to AI
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
