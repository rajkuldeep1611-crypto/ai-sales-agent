import os
import time
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import google.generativeai as genai

# Configuration from Environment Variables
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini API Safely
if GEMINI_API_KEY:
    try:
        genai.configure(
            api_key=GEMINI_API_KEY, 
            client_options={"api_endpoint": "generativelanguage.googleapis.com"}
        )
    except Exception as err:
        print(f"[!] API Configuration warning: {err}")

print("Kuldeep Brothers AI Studio - Global Auto-Reply AI Started")

def check_and_reply_emails():
    if not EMAIL_USER or not EMAIL_PASS:
        print("[!] EMAIL_USER ya EMAIL_PASS setup nahi hai.")
        return

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        status, messages = mail.search(None, '(UNSEEN)')
        if status != 'OK' or not messages[0]:
            mail.logout()
            return

        for num in messages[0].split():
            res, msg_data = mail.fetch(num, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    subject_raw = msg.get("Subject", "No Subject")
                    subject = "No Subject"
                    if subject_raw:
                        decoded_list = decode_header(subject_raw)
                        if decoded_list:
                            sub_part, encoding = decoded_list[0]
                            if isinstance(sub_part, bytes):
                                subject = sub_part.decode(encoding if encoding else "utf-8", errors="ignore")
                            else:
                                subject = str(sub_part)

                    from_email = msg.get("From", "")
                    if not from_email:
                        continue
                        
                    print(f"[+] Client Email From: {from_email}")

                    if "no-reply" in from_email.lower() or "notifications" in from_email.lower():
                        print(f"[i] Ignored automated email from: {from_email}")
                        continue

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body = payload.decode("utf-8", errors="ignore")
                                break
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="ignore")

                    ai_reply = "Hello, thank you for reaching out. We have received your message and will get back to you shortly."
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        prompt = f"Write a professional sales response to this client email:\n\nSubject: {subject}\nMessage: {body}"
                        response = model.generate_content(prompt)
                        if response and response.text:
                            ai_reply = response.text
                    except Exception as e:
                        print(f"[!] AI Generation Error: {e}")

                    msg_reply = MIMEMultipart()
                    msg_reply["From"] = EMAIL_USER
                    msg_reply["To"] = from_email
                    msg_reply["Subject"] = f"Re: {subject}"
                    msg_reply.attach(MIMEText(ai_reply, "plain"))

                    smtp = smtplib.SMTP_SSL(SMTP_SERVER, 465)
                    smtp.login(EMAIL_USER, EMAIL_PASS)
                    smtp.sendmail(EMAIL_USER, from_email, msg_reply.as_string())
                    smtp.quit()
                    print(f"[✔] Reply sent successfully to {from_email}")

        mail.logout()
    except Exception as e:
        print(f"[!] IMAP/SMTP Error: {e}")

if __name__ == "__main__":
    while True:
        check_and_reply_emails()
        time.sleep(60)
