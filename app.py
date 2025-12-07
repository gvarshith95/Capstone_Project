import streamlit as st
from openai import OpenAI
import PyPDF2
import re

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="Recruit-AI", layout="centered")
st.title("Recruit-AI: Resume Screening Assistant")
st.write("Upload a Job Description and Resume to generate an AI-driven screening report.")

# -------------------------
# Helper: Read PDF or Text
# -------------------------
def read_file(uploaded_file):
    if uploaded_file.type == "application/pdf":
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted
        return text
    return uploaded_file.read().decode("utf-8", errors="ignore")


# -------------------------
# Helper: Extract sections from AI output
# -------------------------
def extract_section(label, text):
    pattern = rf"\*\*{label}.*?\*\*:(.*?)(?=\*\*|$)"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else "Not provided."


# -------------------------
# File Upload UI
# -------------------------
jd = st.file_uploader("Upload Job Description (JD)", type=["pdf", "txt"])
resume = st.file_uploader("Upload Resume", type=["pdf", "txt"])

# -------------------------
# Main Process Button
# -------------------------
if st.button("Analyze Candidate"):
    if not jd or not resume:
        st.error("Please upload both Job Description and Resume.")
    else:
        with st.spinner("Analyzing with Recruit-AI..."):

            jd_text = read_file(jd)
            resume_text = read_file(resume)

            prompt = f"""
            You are an HR AI Assistant. Compare the following Resume with the Job Description.

            Return the response in this EXACT STRUCTURE:

            **Fit Score (0-100):**
            <score>

            **Candidate Summary:**
            <3-5 bullet points>

            **Recommended Action (Interview / Hold / Reject):**
            <action>

            **Draft Outreach Email (if Interview Recommended):**
            <email text>

            -------------------------
            Job Description:
            {jd_text}

            Resume:
            {resume_text}
            """

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )

                full_output = response.choices[0].message.content

                # Extract sections
                fit_score = extract_section("Fit Score", full_output)
                summary = extract_section("Candidate Summary", full_output)
                action = extract_section("Recommended Action", full_output)
                email = extract_section("Draft Outreach Email", full_output)

                # -------------------------
                # Tabs UI
                # -------------------------
                tab1, tab2, tab3, tab4 = st.tabs(
                    ["📊 Screening Score", "📝 Summary", "🎯 Recommended Action", "✉️ Email Draft"]
                )

                with tab1:
                    st.subheader("Screening Score")
                    st.write(f"**Candidate Fit Score:** {fit_score}")

                    # Show numeric score bar if it's valid
                    try:
                        score_value = int(re.findall(r"\d+", fit_score)[0])
                        st.progress(score_value / 100)
                    except:
                        st.info("Score not formatted as a number.")

                with tab2:
                    st.subheader("Candidate Summary")
                    st.markdown(summary)

                with tab3:
                    st.subheader("Recommended Action")
                    st.markdown(action)

                with tab4:
                    st.subheader("Email Draft")
                    st.markdown(email)

            except Exception as e:
                st.error("Error while connecting to the AI model.")
                st.text(str(e))
