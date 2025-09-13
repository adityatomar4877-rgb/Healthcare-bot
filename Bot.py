import streamlit as st
import pandas as pd
import random
import re
import string
from langdetect import detect
from difflib import SequenceMatcher

# ========== 0. Small helpers & config ==========
st.set_page_config(page_title="Healthcare Chatbot", page_icon="💊")

# Basic english stopwords (small list to avoid false token matches)
STOPWORDS = {
    "the","and","for","with","from","that","this","these","those","have","has","had",
    "been","was","were","are","is","a","an","in","on","at","by","of","to","or","as",
    "it","be","but","not","so","if","we","you","i","they","he","she","them","his","her"
}

def clean_and_tokenize(text):
    """Lowercase, remove punctuation, split into tokens. Keep tokens length >=3 and not stopwords."""
    if not text or not isinstance(text, str):
        return set()
    # normalize
    text = text.lower()
    # replace punctuation with spaces
    text = re.sub(r"[{}]".format(re.escape(string.punctuation)), " ", text)
    tokens = [t.strip() for t in text.split() if t.strip()]
    # filter
    tokens = [t for t in tokens if len(t) >= 3 and t not in STOPWORDS]
    return set(tokens)

def fuzzy_ratio(a, b):
    return SequenceMatcher(None, a or "", b or "").ratio()

# ========== 1. Load FAQ CSV safely ==========
try:
    faq_df = pd.read_csv("health_faq.csv")
except FileNotFoundError:
    st.error("❌ FAQ file not found. Please upload 'health_faq.csv' in the app directory.")
    st.stop()

# ========== 2. Configure Gemini (optional) ==========
genai = None
gemini_api_key = st.secrets.get("GEMINI_API_KEY", None)
gemini_ready = False
if gemini_api_key:
    try:
        import google.generativeai as genai_module
        genai_module.configure(api_key=gemini_api_key)
        genai = genai_module
        gemini_ready = True
    except Exception as e:
        st.warning(f"Gemini init failed: {e}")
        gemini_ready = False
else:
    st.info("Gemini API key not found in Streamlit secrets. Gemini functions will be disabled until you add GEMINI_API_KEY.")

# ========== 3. Gemini translation & ask helpers ==========
def translate_via_gemini(text, target_lang="en"):
    """Translate text to target_lang using Gemini. Returns original text if Gemini not available."""
    if not gemini_ready or not text or target_lang == "en":
        return text
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(f"Translate the following text to {target_lang}:\n\n{text}")
        return resp.text if resp and getattr(resp, "text", None) else text
    except Exception as e:
        st.warning(f"Translation error with Gemini: {e}")
        return text

def to_english(text):
    """Translate user text to English if Gemini available; else return text as-is."""
    if not gemini_ready or not text:
        return text
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(f"Translate this to English:\n\n{text}")
        return resp.text if resp and getattr(resp, "text", None) else text
    except Exception as e:
        st.warning(f"English translation error: {e}")
        return text

def ask_gemini(user_input_en, target_lang="en"):
    """Ask Gemini (user_input_en should be English). Returns string answer or helpful message."""
    if not gemini_ready:
        return "⚠️ Gemini AI not available. Please add GEMINI_API_KEY in Streamlit secrets to enable AI."
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            f"You are a healthcare awareness assistant. Answer the user's question in {target_lang}. "
            "Never give prescriptions; only provide awareness, prevention, and general guidance.\n\n"
            f"Question: {user_input_en}"
        )
        resp = model.generate_content(prompt)
        return resp.text if resp and getattr(resp, "text", None) else "⚠️ No response from Gemini."
    except Exception as e:
        return f"⚠️ Error while contacting Gemini: {e}"

# ========== 4. Improved FAQ Search (token + fuzzy) ==========
def search_faq(user_input, top_n=3, fuzzy_threshold=0.6, debug=False):
    """
    Returns a list of matching rows (max top_n) IF:
      - token overlap exists (after stopword removal), OR
      - best fuzzy score >= fuzzy_threshold.
    Otherwise returns None (so AI fallback will trigger).
    """
    user_input = (user_input or "").strip()
    if not user_input:
        return None

    user_tokens = clean_and_tokenize(user_input)
    candidates = []

    # scan rows and compute token overlap + fuzzy score
    for _, row in faq_df.iterrows():
        disease = str(row.get("Disease", "") or "")
        symptoms = str(row.get("Common Symptoms", "") or "")
        notes = str(row.get("Notes", "") or "")
        combined_text = " ".join([disease, symptoms, notes]).strip()

        if not combined_text:
            continue

        row_tokens = clean_and_tokenize(combined_text)
        token_overlap = user_tokens.intersection(row_tokens)
        tok_count = len(token_overlap)

        # fuzzy match between raw user input and combined row text
        score = fuzzy_ratio(user_input, combined_text)

        # score weight: If token overlap exists, we boost priority (but still return None only if no strong match)
        priority = score
        if tok_count > 0:
            # give a small boost when meaningful token overlap present
            priority = max(priority, 0.75 + min(0.25, tok_count * 0.05))  # ensures token hits usually pass

        candidates.append((priority, score, tok_count, row))

    if not candidates:
        if debug:
            st.write("DEBUG: No candidates in DB (empty rows).")
        return None

    # sort by priority (descending)
    candidates.sort(key=lambda x: x[0], reverse=True)
    top_candidates = candidates[:top_n]

    # debug info
    if debug:
        dbg = [
            {
                "priority": round(c[0], 3),
                "fuzzy_score": round(c[1], 3),
                "token_hits": c[2],
                "disease": c[3].get("Disease", "N/A")
            } for c in top_candidates
        ]
        st.write("DEBUG - top candidates:", dbg)

    # Decide if top result passes strong-match criteria:
    best_priority, best_fuzzy, best_tok_hits, best_row = top_candidates[0]

    # Strong-match rules:
    # 1) If any token hits exist -> treat as strong match
    # 2) Else if best_fuzzy >= fuzzy_threshold -> treat as strong match
    if best_tok_hits > 0 or best_fuzzy >= fuzzy_threshold:
        return [c[3] for c in top_candidates]
    else:
        return None

# ========== 5. UI elements ==========
st.title("💊 Healthcare & Disease Awareness Chatbot")
st.write("Ask about diseases, symptoms, prevention. Database checked first; AI fallback only if needed.")

# sidebar controls
st.sidebar.header("Settings")
fuzzy_threshold = st.sidebar.slider("Fuzzy match threshold", min_value=0.30, max_value=0.90, value=0.60, step=0.05)
top_n = st.sidebar.slider("Results from database (top n)", 1, 5, 3)
debug_mode = st.sidebar.checkbox("Show debug info", value=False)
st.sidebar.markdown("---")
st.sidebar.markdown("Gemini ready: " + ("✅" if gemini_ready else "❌"))

lang_map = {
    "English": "en",
    "हिंदी (Hindi)": "hi",
    "தமிழ் (Tamil)": "ta",
    "বাংলা (Bengali)": "bn",
    "ગુજરાતી (Gujarati)": "gu",
    "मराठी (Marathi)": "mr",
    "తెలుగు (Telugu)": "te",
    "ಕನ್ನಡ (Kannada)": "kn",
    "മലയാളം (Malayalam)": "ml",
    "ਪੰਜਾਬੀ (Punjabi)": "pa",
    "اردو (Urdu)": "ur",
    "ଓଡ଼ିଆ (Odia)": "or"
}

language_choice = st.selectbox("🌐 Choose Language:", list(lang_map.keys()))
target_lang = lang_map[language_choice]

user_question = st.text_input("Type your question here:")

# AI toggle
force_ai = st.checkbox("🤖 Ask AI Directly (skip database)")

# detect language for UI convenience (doesn't affect matching if Gemini unavailable)
if user_question.strip():
    try:
        detected_lang = detect(user_question)
        if detected_lang in lang_map.values() and detected_lang != target_lang:
            st.info(f"🌐 Auto-detected language: {detected_lang.upper()} (will display results in selected language)")
    except Exception:
        pass

# ========== 6. Submit logic ==========
submit = st.button("🔍 Search")
if submit and user_question:
    # Convert to English for search/AI if possible, else use raw text
    query_in_english = to_english(user_question) if gemini_ready else user_question

    if force_ai:
        with st.spinner("🤖 Asking Gemini AI..."):
            answer_en = ask_gemini(query_in_english, "en")
            answer_final = translate_via_gemini(answer_en, target_lang)
            st.success(answer_final)

    else:
        matches = search_faq(query_in_english, top_n=top_n, fuzzy_threshold=fuzzy_threshold, debug=debug_mode)
        if matches:
            st.subheader("📋 Best Matches from Database:")
            for row in matches:
                block = (
                    f"**Disease:** {row.get('Disease','N/A')}\n\n"
                    f"**Symptoms:** {row.get('Common Symptoms','N/A')}\n\n"
                    f"**Notes:** {row.get('Notes','N/A')}\n\n"
                    f"**Severity:** {row.get('Severity Tagging','N/A')}\n\n"
                    f"**Advice:** {row.get('Disclaimers & Advice','N/A')}"
                )
                displayed = translate_via_gemini(block, target_lang) if target_lang != "en" else block
                st.info(displayed)
                st.markdown("---")
        else:
            # fallback to AI
            with st.spinner("🤖 No useful DB match, asking Gemini AI..."):
                answer_en = ask_gemini(query_in_english, "en")
                answer_final = translate_via_gemini(answer_en, target_lang)
                st.success(answer_final)

# ========== 7. Extras ==========
if st.button("💡 Show me a random health tip"):
    tips = [
        "Wash your hands regularly with soap and water.",
        "Drink at least 2–3 liters of clean water every day.",
        "Use mosquito nets to prevent vector-borne diseases.",
        "Eat fresh fruits and vegetables daily.",
        "Exercise at least 30 minutes every day."
    ]
    tip = random.choice(tips)
    tip = translate_via_gemini(tip, target_lang)
    st.warning(tip)

if st.button("🆘 Emergency / SOS (Call 108)"):
    sos_message = (
        "🚨 If this is a medical emergency, please call **108** immediately "
        "or contact your nearest healthcare provider.\n\n"
        "[📞 Call 108](tel:108)"
    )
    sos_message = translate_via_gemini(sos_message, target_lang)
    st.error(sos_message)
