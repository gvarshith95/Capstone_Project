import streamlit as st
from openai import OpenAI
import PyPDF2
import json
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# ============================================
#  OPENAI INIT
# ============================================
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ============================================
#  PAGE CONFIG + GLOBAL UI STYLING
# ============================================
st.set_page_config(page_title="Recruit-AI", layout="centered")

st.markdown("""
<style>

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #2B2D42;
}

/* Full-page gradient background */
.stApp {
    background: linear-gradient(135deg, #EFF3F6 0%, #E4EBF1 40%, #F7F9FB 100%);
    background-attachment: fixed;
}

/* Page container */
.main {
    max-width: 900px;
    margin: 0 auto;
    padding-top: 30px;
}

/* Header branding */
.header-title {
    font-size: 42px;
    font-weight: 800;
    color: #1A1D29;
    text-align: center;
    margin-bottom: -5px;
}

.header-subtitle {
    font-size: 18px;
    font-weight: 400;
    color: #4B5563;
    text-align: center;
    margin-bottom: 30px;
}

/* Glassmorphism card style */
.card {
    background: rgba(255, 255, 255, 0.65);
    backdrop-filter: blur(14px) saturate(180%);
    -webkit-backdrop-filter: blur(14px) saturate(180%);
    border-radius: 18px;
    padding: 28px 32px;
    margin-bottom: 32px;
    border: 1px solid rgba(255, 255, 255, 0.35);
    box-shadow: 0px 6px 28px rgba(0,0,0,0.08);
}

/* Tabs */
.stTabs [role="tab"] {
    padding: 12px 20px;
    font-size: 16px;
    font-weight: 600;
    border-radius: 10px;
    transition: all 0.3s ease;
}

.stTabs [role="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #EF233C, #D90429);
    color: white !important;
    box-shadow: 0px 4px 12px rgba(239, 35, 60, 0.4);
}

.stTabs [role="tab"][aria-selected="false"] {
    background: #EDF2F4;
    color: #2B2D42 !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stTextArea textarea {
    border-radius: 10px !important;
    border: 1px solid #CBD5E0 !important;
    padding: 10px !important;
}

/* File upload styling */
.stFileUploader {
    background: rgba(255, 255, 255, 0.65);
    padding: 18px;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.4);
}

/* Primary button */
.stButton>button {
    background: linear-gradient(135deg, #EF233C, #D90429);
    color: white;
    border-radius: 12px;
    padding: 13px 22px;
    border: none;
    font-size: 17px;
    font-weight: 600;
    transition: 0.25s;
}

.stButton>button:hover {
    background: linear-gradient(135deg, #D90429, #EF233C);
    transform: scale(1.02);
}

/* Alerts */
.stAlert {
    border-radius: 12px !important;
    padding: 14px !important;
}

/* Progress bar */
.stProgress > div > div > div {
    background: linear-gradient(135deg, #06D6A0, #1B9C85) !important;
}

/* Email text area */
textarea {
    background: rgba(255,255,255,0.7) !important;
    border-radius: 12px !important;
}

/* Improve spacing between elements */
.block-container {
    padding-top: 2rem;
}

</style>
""", unsafe_allow_html=True)

# ============================================
#  HEADER
# ============================================
st.markdown("""
<div class="header-title">Recruit-AI</div>
<div class="header-subtitle">Smarter candidate screening for modern hiring teams</div>
""", unsafe_allow_html=True)


# ============================================
#  HELPERS
# ============================================
def read_file(uploaded_file):
    """Extract text from PDF or TXT."""
    if uploaded_file.type == "application/pdf":
        reader = PyPDF2.PdfReader(uploaded_file)
        return "".join(page.extract_text() or "" for page in reader.pages)
    return uploaded_file.read().decode("utf-8", errors="ignore")


def repair_json(bad_json):
    """Clean and repair LLM JSON output."""
    cleaned = bad_json.replace("```", "").replace("json", "").strip()
    cleaned = cleaned.replace(",}", "}").replace(",]", "]")
    cleaned = "".join(c for c in cleaned if ord(c) >= 32)
    return cleaned


def send_email(to_email, subject, content):
    """Send email using SendGrid."""
    try:
        message = Mail(
            from_email=st.secrets["SENDER_EMAIL"],
            to_emails=to_email,
            subject=subject,
            html_content=content.replace("\n", "<br>")
        )
        sg = SendGridAPIClient(st.secrets["SENDGRID_API_KEY"])
        response = sg.send(message)
        return response.status_code
    except Exception as e:
        return str(e)


# ============================================
#  UPLOAD SECTION (CARD)
# ============================================
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("📄 Upload Job Description & Resume")

jd = st.file_uploader("Upload Job Description", type=["pdf", "txt"])
resume = st.file_uploader("Upload Candidate Resume", type=["pdf", "txt"])
st.markdown('</div>', unsafe_allow_html=True)


# ============================================
#  ANALYZE BUTTON
# ============================================
st.markdown('<div style="text-align:center;">', unsafe_allow_html=True)
run_button = st.button("🔍 Analyze Candidate")
st.markdown('</div>', unsafe_allow_html=True)


# ============================================
#  MAIN AI LOGIC
# ============================================
if run_button:
    if not jd or not resume:
        st.error("Please upload both JD and Resume.")
        st.stop()

    with st.spinner("Analyzing candidate with Recruit-AI…"):

        jd_text = read_file(jd)
        resume_text = read_file(resume)

        prompt = f"""
        You are an expert HR screening assistant. Return ONLY valid JSON.

        REQUIRED FORMAT:
        {{
          "fit_score": <number>,
          "summary": "<3-5 bullet points>",
          "action": "<Interview | Hold | Reject>",
          "email": "<email draft>"
        }}

        Do NOT add explanations.

        Job Description:
        {jd_text}

        Resume:
        {resume_text}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        raw_output = response.choices[0].message.content
        cleaned = repair_json(raw_output)

        try:
            data = json.loads(cleaned)
        except:
            st.error("AI returned malformed JSON.")
            st.code(raw_output)
            st.stop()

        fit_score = data.get("fit_score")
        summary = data.get("summary", "")
        action = data.get("action", "")
        email_text = data.get("email", "")


        # ============================================
        #  TABS UI
        # ============================================
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📊 Screening Score", "📝 Summary", "🎯 Action", "✉️ Email Draft"]
        )

        # --- TAB 1 ---
        with tab1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("📊 Screening Score")
            if isinstance(fit_score, int):
                st.write(f"### Fit Score: **{fit_score}/100**")
                st.progress(fit_score / 100)
            else:
                st.warning("Score unavailable.")
            st.markdown('</div>', unsafe_allow_html=True)

        # --- TAB 2 ---
        with tab2:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("📝 Candidate Summary")
            st.markdown(summary)
            st.markdown('</div>', unsafe_allow_html=True)

        # --- TAB 3 ---
        with tab3:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("🎯 Recommended Action")
            st.markdown(f"## {action}")
            st.markdown('</div>', unsafe_allow_html=True)

        # --- TAB 4 ---
        with tab4:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("✉️ Email Draft")

            editable_email = st.text_area("Edit Before Sending:", email_text, height=250)
            recipient = st.text_input("Candidate Email")

            if st.button("Send Email"):
                if not recipient:
                    st.error("Enter a recipient email.")
                else:
                    status = send_email(recipient, "Interview Invitation – Recruit-AI", editable_email)
                    if str(status).startswith("2"):
                        st.success("Email sent successfully!")
                    else:
                        st.error(f"Failed to send email: {status}")

            st.markdown('</div>', unsafe_allow_html=True)
