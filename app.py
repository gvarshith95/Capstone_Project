import streamlit as st
from openai import OpenAI
import PyPDF2
import json
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# -------------------------
# Initialize OpenAI client
# -------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.set_page_config(page_title="Recruit-AI", layout="centered")
st.title("Recruit-AI: Resume Screening Assistant")
st.write("Upload a Job Description and Resume to generate an AI-driven screening report.")


# -------------------------
# Helper: Read PDF or Text File
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
# Helper: Send Email (SendGrid)
# -------------------------
def send_email(to_email, subject, content):
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


# -------------------------
# Upload Inputs
# -------------------------
jd = st.file_uploader("Upload Job Description (JD)", type=["pdf", "txt"])
resume = st.file_uploader("Upload Resume", type=["pdf", "txt"])


# -------------------------
# Analyze Button
# -------------------------
if st.button("Analyze Candidate"):
    if not jd or not resume:
        st.error("Please upload both Job Description and Resume.")
    else:
        with st.spinner("Analyzing with Recruit-AI..."):
            jd_text = read_file(jd)
            resume_text = read_file(resume)

            # -------------------------
            # JSON Prompt
            # -------------------------
            prompt = f"""
            You are an HR AI assistant. Return ONLY valid JSON.

            Use this EXACT structure:

            {{
              "fit_score": <number>,
              "summary": "<3-5 bullet points>",
              "action": "<Interview | Hold | Reject>",
              "email": "<outreach email draft>"
            }}

            Do not add explanations. Do not add text outside JSON.

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

                raw_output = response.choices[0].message.content

                # -------------------------
                # Parse JSON output safely
                # -------------------------
                try:
                    data = json.loads(raw_output)
                except:
                    st.error("AI did not return valid JSON. Showing raw output.")
                    st.write(raw_output)
                    st.stop()

                fit_score = data.get("fit_score")
                summary = data.get("summary", "")
                action = data.get("action", "")
                email = data.get("email", "")

                # -------------------------
                # Display Results in Tabs
                # -------------------------
                tab1, tab2, tab3, tab4 = st.tabs(
                    ["📊 Screening Score", "📝 Summary", "🎯 Recommended Action", "✉️ Email Draft"]
                )

                # --- Screening Tab
                with tab1:
                    st.subheader("Screening Score")

                    if isinstance(fit_score, int):
                        st.write(f"**Candidate Fit Score:** {fit_score}")
                        st.progress(fit_score / 100)
                    else:
                        st.warning("Score not provided or not a valid number.")

                # --- Summary Tab
                with tab2:
                    st.subheader("Candidate Summary")
                    st.markdown(summary)

                # --- Action Tab
                with tab3:
                    st.subheader("Recommended Action")
                    st.markdown(f"### {action}")

                # --- Email Draft Tab
                with tab4:
                    st.subheader("Email Draft")
                    editable_email = st.text_area("Edit email before sending:", email, height=250)

                    recipient = st.text_input("Recipient Email")

                    if st.button("Send Email"):
                        if not recipient:
                            st.error("Please enter the candidate's email address.")
                        else:
                            status = send_email(
                                to_email=recipient,
                                subject="Interview Invitation - Recruit-AI",
                                content=editable_email
                            )
                            if str(status).startswith("2"):
                                st.success("Email sent successfully!")
                            else:
                                st.error(f"Failed to send email. Error: {status}")

            except Exception as e:
                st.error("Error while connecting to the AI model.")
                st.text(str(e))
