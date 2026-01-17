import streamlit as st
from groq import Groq
import json
import time
from dotenv import load_dotenv
import os
import pandas as pd
import random

# --- SETUP ---
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY"))

# --- CONFIG ---
st.set_page_config(page_title="Selective Master AI", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stTextArea textarea { font-size: 1.15rem !important; border-radius: 10px; line-height: 1.6; }
    .locked-box { background-color: #f1f5f9; border: 2px dashed #cbd5e1; padding: 80px 20px; text-align: center; border-radius: 15px; color: #64748b; margin-top: 50px; }
    .result-container { background-color: #ffffff; padding: 30px; border-radius: 15px; border: 1px solid #e2e8f0; margin-top: 30px; }
    </style>
""", unsafe_allow_html=True)

# --- TOPIC BANK (20 items) ---

def load_topics():
    try:
        with open('topics.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback if file is missing
        return [{"title": "Error", "type": "N/A", "prompt": "topics.json not found."}]
    
TOPIC_BANK = load_topics()

# --- GRADING LOGIC ---
def get_level(score, max_val):
    pct = (score / max_val) * 10
    if pct >= 8: return "More Than Adequate", 3
    if pct >= 5.5: return "Adequate", 2
    if pct >= 4.5: return "Just Adequate", 1
    return "Not Adequate", 0

def calculate_award(levels, scores):
    mta = levels.count(3)
    adq = levels.count(2)
    jad = levels.count(1)
    nad = levels.count(0)
    
    # Mathematical Override: Content score < 6 cannot be HD
    content_score = scores.get('Content', 0)
    
    if mta >= 2 and (mta + adq) == 4 and content_score >= 6: return "🏆 High Distinction"
    if mta >= 1 and (mta + adq) == 4: return "🏅 Distinction"
    if adq >= 2 and (adq + jad + mta) == 4: return "📜 Credit"
    if nad == 0: return "✅ Pass"
    
    if nad == 1: return "❌ F3 (One Failed)"
    if nad == 2: return "❌ F2 (Two Failed)"
    if nad == 3: return "❌ F1 (Three Failed)"
    return "💀 F0 (Everything Failed)"

# --- SESSION STATE ---
if 'test_active' not in st.session_state: st.session_state.test_active = False
if 'start_time' not in st.session_state: st.session_state.start_time = None
if 'current_topic' not in st.session_state: st.session_state.current_topic = None
if 'analysis_result' not in st.session_state: st.session_state.analysis_result = None
if 'submitted_essay' not in st.session_state: st.session_state.submitted_essay = None

# --- TIMER ---
@st.fragment(run_every=1.0)
def timer_ui(timed_mode):
    if st.session_state.test_active and timed_mode:
        elapsed = time.time() - st.session_state.start_time
        remaining = max(0, (30 * 60) - elapsed)
        mins, secs = divmod(int(remaining), 60)
        st.metric("⏳ Time Remaining", f"{mins:02d}:{secs:02d}")
        if remaining <= 0:
            st.session_state.test_active = False
            st.rerun()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings & Rules")
    st.markdown("""
    **Award Thresholds:**
    - **HD**: 2x More than Adequate, rest Adequate.
    - **D**: 1x More than Adequate, rest Adequate.
    - **C**: 2x Adequate, rest Just Adequate.
    - **Pass**: All at least Just Adequate.
    
    **Levels (Scaled to 10):**
    - **8.0+**: More Than Adequate
    - **5.5 - 7.9**: Adequate
    - **4.5 - 5.4**: Just Adequate
    - **Below 4.5**: Not Adequate
    """)
    mode = st.radio("Exam Mode:", ["Timed (30 mins)", "Unlimited Practice"])
    is_timed = "Timed" in mode
    
    if not st.session_state.test_active:
        if st.button("🚀 START EXAM", type="primary", use_container_width=True):
            st.session_state.current_topic = random.choice(TOPIC_BANK)
            st.session_state.start_time = time.time()
            st.session_state.test_active = True
            st.session_state.analysis_result = None
            st.session_state.submitted_essay = None
            st.rerun()
    else:
        if st.button("🛑 Reset Everything", use_container_width=True):
            st.session_state.test_active = False
            st.session_state.submitted_essay = None
            st.rerun()

# --- MAIN UI ---
st.title("🚀 Selective Master AI")

if not st.session_state.test_active and st.session_state.analysis_result is None:
    st.markdown('<div class="locked-box"><h1>Exam Paper Face Down</h1><p>Start from the sidebar.</p></div>', unsafe_allow_html=True)

elif st.session_state.test_active or st.session_state.analysis_result:
    t_col1, t_col2 = st.columns([3, 1])
    with t_col1:
        st.subheader(f"Topic: {st.session_state.current_topic['title']}")
        st.text(f"Task: {st.session_state.current_topic['prompt']}")
    with t_col2: 
        if st.session_state.test_active:
            timer_ui(is_timed)

    if st.session_state.test_active:
        essay_input = st.text_area("Your Response:", height=500)
        wc = len(essay_input.split())
        st.markdown(f"**Word Count:** `{wc}`")
        
        if st.button("🏁 Finish & Grade", type="primary"):
            with st.spinner("Strict Marking..."):
                try:
                    if not essay_input.strip():
                        st.error("Please write something before submitting.")
                    elif len(essay_input.split()) < 10:
                        st.error("Please write at least 10 words before submitting.")
                    else:
                        st.session_state.submitted_essay = essay_input
                        chat_completion = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            response_format={"type": "json_object"},
                            messages=[
                                {
                                    "role": "system", 
                                    "content": """You are an ELITE and CRITICAL NSW Selective School Writing Examiner and high-performance coach. 
                                    Your grading is harsh, pedantic, and high-stakes. 
                                    
                                    STRICT GRADING RULES:
                                    1. LANGUAGE: If vocabulary is basic (e.g., 'stuff', 'nice', 'bad', 'scared', 'big'), Language score MUST NOT exceed 2/5.
                                    2. CONTENT: If the story is a simple chronological recount ('I did this, then that') without deep sensory imagery or emotional resonance, Content MUST NOT exceed 3/8.
                                    3. STRUCTURE: Award 4/4 only if there is a sophisticated hook, seamless transitions, and a powerful resolution.
                                    4. ACCURACY: One single comma splice or tense shift drops Accuracy to 2/3. Three or more errors drop it to 1/3.
                                    
                                    REQUIRED JSON STRUCTURE:
                                    {
                                    "scores": {
                                        "Content": {"score": 0, "reason": "why this score", "improvement": "how to improve"},
                                        "Structure": {"score": 0, "reason": "why this score", "improvement": "how to improve"},
                                        "Language": {"score": 0, "reason": "why this score", "improvement": "how to improve"},
                                        "Accuracy": {"score": 0, "reason": "why this score", "improvement": "how to improve"}
                                    },
                                    "feedback": {"strengths": [], "weaknesses": []},
                                    "paragraph_rewrite": "full paragraph rewrite if total score <16, else empty string"
                                    }
                                    
                                    If scores are maxed, weaknesses can be empty. If scores are zero, strengths can be empty."""
                                },
                                {"role": "user", "content": f"Topic: {st.session_state.current_topic['prompt']}\nEssay: {essay_input}"}
                            ]
                        )
                        response_text = chat_completion.choices[0].message.content
                        try:
                            st.session_state.analysis_result = json.loads(response_text)
                        except json.JSONDecodeError:
                            st.error(f"Failed to parse AI response. Response: {response_text}")
                        else:
                            st.session_state.test_active = False
                            st.rerun()
                except Exception as e: st.error(f"Error: {e}")
    else:
        # Display the submitted answer
        st.text_area("Your Response:", value=st.session_state.get('submitted_essay', ''), height=500, disabled=True)
        wc = len(st.session_state.get('submitted_essay', '').split())
        st.markdown(f"**Word Count:** `{wc}`")

# --- RESULTS ---
if st.session_state.analysis_result:
    res = st.session_state.analysis_result
    scores_raw = res.get('scores', {})
    
    # Extract scores
    scores = {k: v['score'] if isinstance(v, dict) else v for k, v in scores_raw.items()}
    
    # Calculate Levels
    results_data = []
    level_values = []
    total_raw = 0
    for cat, max_val in [("Content", 8), ("Structure", 4), ("Language", 5), ("Accuracy", 3)]:
        val = scores.get(cat, 0)
        label, rank = get_level(val, max_val)
        reason = scores_raw.get(cat, {}).get('reason', '') if isinstance(scores_raw.get(cat), dict) else ''
        improvement = scores_raw.get(cat, {}).get('improvement', '') if isinstance(scores_raw.get(cat), dict) else ''
        results_data.append({"Criteria": cat, "Score": val, "Max": max_val, "Level": label, "Reason": reason, "Improvement": improvement})
        level_values.append(rank)
        total_raw += val

    award = calculate_award(level_values, scores)
    
    st.divider()
    st.markdown('<div class="result-container">', unsafe_allow_html=True)
    st.header("📊 Final Marking Report")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Overall Award", award)
    m2.metric("Total Score", f"{total_raw}/20")
    m3.metric("Status", "Complete")

    st.write("### 📈 Section Feedback")
    df = pd.DataFrame(results_data)
    df.index = range(1, len(df) + 1)
    st.table(df)

    c1, c2 = st.columns(2)
    fb = res.get('feedback', {})
    if isinstance(fb, list):
        strengths = fb[0] if len(fb) > 0 else []
        weaknesses = fb[1] if len(fb) > 1 else []
    else:
        strengths = fb.get('strengths', [])
        weaknesses = fb.get('weaknesses', [])
    with c1: st.success("**Strengths**\n" + "\n".join([f"- {s}" for s in strengths]))
    with c2: st.error("**Weaknesses**\n" + "\n".join([f"- {w}" for w in weaknesses]))

    paragraph_rewrite = res.get('paragraph_rewrite', '')
    if paragraph_rewrite and total_raw < 16:
        st.write("### 🔧 Paragraph Rewrite")
        st.info(paragraph_rewrite)

    st.markdown('</div>', unsafe_allow_html=True)
    if st.button("🆕 New Practice"):
        st.session_state.analysis_result = None
        st.session_state.submitted_essay = None
        st.rerun()