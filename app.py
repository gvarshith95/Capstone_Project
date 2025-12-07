import streamlit as st
import openai

st.title("Recruit-AI: Resume Screening Agent")

jd = st.file_uploader("Upload Job Description (JD)", type=["txt", "pdf"])
resume = st.file_uploader("Upload Resume", type=["txt", "pdf"])

if st.button("Analyze Candidate"):
    if not jd or not resume:
        st.error("Please upload both JD and Resume")
    else:
        jd_text = jd.read().decode("utf-8", errors="ignore")
        resume_text = resume.read().decode("utf-8", errors="ignore")

        prompt = f"""
        Compare the following resume to the job description. Provide:
        1. A fit score from 0-100.
        2. A short summary of the candidate.
        3. A recommended action (Interview, Reject, Hold).
        4. Bonus: Draft an email for interviewing the candidate.

        Job Description:
        {jd_text}

        Resume:
        {resume_text}
        """

        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        st.subheader("AI Analysis")
        st.write(response.choices[0].message["content"])
