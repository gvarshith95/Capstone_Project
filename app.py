import streamlit as st
from openai import OpenAI
import PyPDF2

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("Recruit-AI: Resume Screening Agent")

jd = st.file_uploader("Upload Job Description (JD)", type=["txt", "pdf"])
resume = st.file_uploader("Upload Resume", type=["txt", "pdf"])


def read_file(file):
    if file.type == "application/pdf":
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    else:
        return file.read().decode("utf-8", errors="ignore")


if st.button("Analyze Candidate"):
    if not jd or not resume:
        st.error("Please upload both JD and Resume")
    else:
        jd_text = read_file(jd)
        resume_text = read_file(resume)

        prompt = f"""
        Compare the following resume to the job description. Provide:
        - A fit score (0-100)
        - A short candidate summary
        - A recommended action (Interview, Reject, Hold)
        - Bonus: Draft an outreach email for the candidate

        Job Description:
        {jd_text}

        Resume:
        {resume_text}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        st.subheader("AI Analysis")
        st.write(response.choices[0].message["content"])
