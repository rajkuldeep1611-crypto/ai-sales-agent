import os
import time
import threading
import imaplib
import email
from email.header import decode_header
import requests
from flask import Flask
import google.generativeai as genai

app = Flask(__name__)

@app.route("/")
def home():
    return "AI Sales Agent is running live 24/7!"

EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 512,
}
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config
)

def send_email(to_email, subject, body):
    try:
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": "Acme <onboarding@resend.dev>",
            "to": [to_email],
            "subject": f"Re: {subject}" if not subject.lower().startswith("re:") else subject,
            "text": body
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code in [200, 201]:
            print(f"--> SUCCESS: Reply sent to {to_email}", flush=True)
        else:
            print(f"Email Sending Error: {response.text}", flush=True)
    except Exception as e:
        print(f"Email Sending Error: {e}", flush=True)

def generate_ai_response(sender_email, subject, email_body):
    prompt = f"""
    You are a professional AI sales assistant. Write a polite, professional, and engaging sales reply to the following customer email.
    
    Customer Email: {email_body}
    Subject: {subject}
    
    Keep the response concise and helpful.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini API Error: {e}", flush=True)
        return "Thank you for reaching out! We have received your message and will get back to you shortly."

def process_inbox():
    print("=== AI Sales Agent Initialized ===", flush=True)
    while True:
        try:
            print("Checking inbox for unread emails...", flush=True)
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(EMAIL_USER, EMAIL_PASS)
            mail.select("inbox")

            status, messages = mail.search(None, '(UNSEEN)')
            if status == "OK":
                email_ids = messages[0].split()
                for e_id in email_ids:
                    res, msg_data = mail.fetch(e_id, "(RFC822)")
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            subject_header = decode_header(msg["Subject"])[0]
                            subject = subject_header[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(subject_header[1] or "utf-8", errors="ignore")
                            
                            from_header = msg.get("From")
                            sender_email = email.utils.parseaddr(from_header)[1]
                            
                            # Self-email loop prevention
                            if sender_email.lower() == EMAIL_USER.lower():
                                continue
                            
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                        break
                            else:
                                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                            print(f"NEW EMAIL DETECTED -> From: {sender_email} | Subject: {subject}", flush=True)
                            
                            ai_reply = generate_ai_response(sender_email, subject, body)
                            send_email(sender_email, subject, ai_reply)
                            
            mail.logout()
        except Exception as e:
            print(f"IMAP Loop Error: {e}", flush=True)
            
        time.sleep(30)

if __name__ == "__main__":
    t = threading.Thread(target=process_inbox, daemon=True)
    t.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
