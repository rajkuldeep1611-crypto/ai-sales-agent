import os
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import google.generativeai as genai
import imaplib
import email
from email.header import decode_header
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- DUMMY WEB SERVER FOR RENDER PORT BINDING ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"AI Sales Agent is Running Live!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    print(f"Web server started on port {port}")
    server.serve_forever()

# Start Web Server in Background Thread
threading.Thread(target=run_web_server, daemon=True).start()

# --- GEMINI & EMAIL SETUP ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def generate_ai_reply(sender_email, subject, body):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
        You are a professional AI Sales Agent. Respond politely and concisely to the customer email.
        From: {sender_email}
        Subject: {subject}
        Body: {body}
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating AI reply: {e}")
        return None

def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = f"Re: {subject}" if not subject.startswith("Re:") else subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())
        server.quit()
        print(f"--> Successfully sent reply to {to_email}")
    except Exception as e:
        print(f"Error sending email: {e}")

def check_and_respond_emails():
    try:
        print("Checking for new emails...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()

        if not email_ids:
            print("No unseen emails found.")

        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")
                    
                    sender = msg.get("From")
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    print(f"New email found from: {sender} | Subject: {subject}")
                    ai_reply = generate_ai_reply(sender, subject, body)
                    if ai_reply:
                        send_email(sender, subject, ai_reply)

        mail.close()
        mail.logout()
    except Exception as e:
        print(f"Error checking emails: {e}")

print("AI Sales Agent Started Successfully...")

# Infinite loop with 60-second polling interval
while True:
    check_and_respond_emails()
    time.sleep(60)
