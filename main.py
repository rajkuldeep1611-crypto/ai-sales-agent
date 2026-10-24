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

# Health Check Server for Render
PORT = int(os.environ.get("PORT", 10000))

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"AI Sales Agent Active")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return  # Keep logs clean

def start_http_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=start_http_server, daemon=True).start()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY not found in environment variables!", flush=True)

def generate_ai_reply(sender_email, subject, body):
    # Multiple working fallback model names if one throws 404
    candidate_models = ["gemini-2.0-flash", "gemini-1.5-flash-8b", "gemini-1.5-pro"]
    
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            prompt = f"You are a helpful AI sales agent. Reply professionally to this email.\nFrom: {sender_email}\nSubject: {subject}\nBody: {body}"
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            print(f"Model {model_name} failed: {e}. Trying next model...", flush=True)
            continue
            
    print("All Gemini models failed to respond.", flush=True)
    return None

def send_email(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = f"Re: {subject}" if not subject.lower().startswith("re:") else subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())
        server.quit()
        print(f"--> SUCCESS: Reply sent to {to_email}", flush=True)
    except Exception as e:
        print(f"Email Sending Error: {e}", flush=True)

def process_inbox():
    try:
        print("Checking inbox for unread emails...", flush=True)
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        status, response = mail.search(None, "UNSEEN")
        email_ids = response[0].split()

        if not email_ids:
            print("No new unread emails found.", flush=True)

        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")
                    
                    sender = email.utils.parseaddr(msg.get("From"))[1]
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()

                    print(f"NEW EMAIL DETECTED -> From: {sender} | Subject: {subject}", flush=True)
                    ai_reply = generate_ai_reply(sender, subject, body)
                    if ai_reply:
                        send_email(sender, subject, ai_reply)

        mail.close()
        mail.logout()
    except Exception as e:
        print(f"IMAP Error: {e}", flush=True)

print("=== AI Sales Agent Initialized ===", flush=True)

while True:
    process_inbox()
    time.sleep(60)
