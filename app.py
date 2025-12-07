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
}

/* App container width */
.main {
    max-width: 900px;
    margin: 0 auto;
}

/* Header styling */
.header-title {
    font-size: 38px;
    font-weight: 700;
    color: #2B2D42;
    margin-bottom: 0px;
}
.header-subtitle {
    font-size: 18px;
    color: #6c757d;
    margin-top: -12px;
}

/* Card container */
.card {
    background-color: #ffffff;
    padding: 22px 28px;
    border-radius: 14px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    margin-bottom: 30px;
}

/* Tabs */
.stTabs [role="tab"] {
    font-size: 17px;
    padding: 10px 20px;
    font-weight: 600;
    border-radius: 6px;
}

.stTabs [role="tab"][aria-selected="true"] {
    background: #EF233C !important;
    color: white !important;
}

.stTabs [role="tab"][aria-selected="false"] {
    background: #EDF2F4;
    color: #2B2D42;
}

/* Primary button */
.stButton>button {
    background-color: #EF233C;
    color: white;
    border-radius: 8px;
    padding: 12px 20px;
    border: None;
    font-size: 17px;
    font-weight: 600;
}
.stButton>button:hover {
    background-color: #D90429;
}

</style>
""", unsafe_allow_html=True)

# ============================================
#  HEADER
# ============================================
st.markdown("""
<div class="header-title">Recruit-AI</div>
<div class="header-subtitle">AI-powered candidate screening for modern hiring teams</div>
""", unsafe_allow_html=True)

# ============================================
#  HELPER: Read PDF + TXT
# ============================================
def read_file(uploaded_file):
    if uploaded_file.type == "application/pdf":
        reader = PyPDF2.PdfReader(uploaded_file)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        return text
    return uploaded_file.read().decode("utf-8", errors="ignore")

# ============================================
#  HELPER: REPAIR AI JSON OUTPUT
# ============================================
def repair_json(bad_json):
    cleaned = bad_json.replace("```", "").replace("json", "").strip()
    cleaned = cleaned.replace(",}", "}").replace(",]", "]")
    cleaned = "".join(c for c in cleaned if ord(c) >= 32)  # Remove illegal chars
    return cleaned

# ============================================
#  HELPER: SEND EMAIL
# ============================================
def send_email(to_email, subject, content):
    try:
        message = Mail(
            from_email=st.secrets["SENDER_EMAIL"],
            to_emails=to_email,
            subject=subject,
            html_content=content.replace("\n", "<br>")
        )

        sg = SendGridAPIClient(st.secrets["SENDGRID_API_KEY"])
        res = sg.send(message)
        return res.status_code

    except Exception as e:
        return str(e)

# ============================================
#  UPLOAD SECTION (CARD)
# ============================================
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("📄 Upload Candidate & Job Files")

jd = st.file_uploader("Job Description (JD)", type=["pdf", "txt"])
resume = st.file_uploader("Candidate Resume", type=["pdf", "txt"])

st.markdown('</div>', unsafe_allow_html=True)

# ============================================
#  ANALYZE BUTTON
# ============================================
st.markdown('<div style="text-align:center;">', unsafe_allow_html=True)
run_button = st.button("🔍 Analyze Candidate")
st.markdown('</div>', unsafe_allow_html=True)

# ============================================
#  MAIN LOGIC
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
          "email": "<interview outreach email>"
        }}

        Do NOT add any text outside JSON.

        Job Description:
        {jd_text}

        Resume:
        {resume_text}
        """

        # OpenAI call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        raw_output = response.choices[0].message.content

        # JSON repair
        cleaned = repair_json(raw_output)

        try:
            data = json.loads(cleaned)
        except:
            st.error("AI returned malformed JSON. Showing raw output:")
            st.code(raw_output)
            st.stop()

        fit_score = data.get("fit_score")
        summary = data.get("summary", "")
        action = data.get("action", "")
        email_text = data.get("email", "")

# ============================================
#  TABS SECTION
# ============================================
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📊 Screening Score", "📝 Summary", "🎯 Action", "✉️ Email Draft"]
        )

        # --- TAB 1 ---
        with tab1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("📊 Screening Score")

            if isinstance(fit_score, int):
                st.write(f"### Fit Score: **{fit_score} / 100**")
                st.progress(fit_score / 100)
            else:
                st.warning("Invalid or missing score.")

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
                    status = send_email(
                        recipient,
                        "Interview Invitation – Recruit-AI",
                        editable_email
                    )
                    if str(status).startswith("2"):
                        st.success("Email sent successfully!")
                    else:
                        st.error(f"Failed to send email: {status}")

            st.markdown('</div>', unsafe_allow_html=True)
