import os
import time
import imaplib
import email
from email.header import decode_header
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from google import genai
except ImportError:
    genai = None

# ================= CONFIGURATION =================
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_USER = "rajkuldeep1611@gmail.com"
EMAIL_PASS = "uoyqxomuditgmdyn"

# Gemini API Key set
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6I9cl9sTn98dG0BRA1XS1sU56qHTgvSFHzoyK8qM5Fc1Q") 

def get_global_ai_reply(client_email_text):
    """Client ki global language detect karke native language mein sales reply generate karta hai."""
    prompt = f"""
    You are the Senior Global AI Sales Consultant for 'Kuldeep Brothers AI Studio'.
    We received a reply from an international client regarding our AI Automation services:
    
    CLIENT EMAIL CONTENT:
    "{client_email_text}"
    
    Your Instructions:
    1. Detect the language of the client's message automatically.
    2. Write the reply STRICTLY in the exact same language/dialect the client used (French, Spanish, German, Japanese, English, Hindi, etc.).
    3. Understand their query and highlight how our AI automation saves time and cuts costs.
    4. Primary Goal: Persuade them to book a quick 10-minute discovery call or WhatsApp meeting.
    5. Maintain a polite, highly professional business tone.
    6. Output ONLY the email body text without markdown formatting or introductory commentary.
    """
    
    if not genai:
        print("[!] Error: 'google-genai' package is not installed.")
        return None

    try:
        # Client initialization with fallback models
        ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else genai.Client()
        
        try:
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"[!] gemini-2.5-flash error: {e}. Trying fallback model...")
            response = ai_client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt
            )
            return response.text.strip()

    except Exception as e:
        print(f"[!] AI Generation Error: {e}")
        return None

def send_email_reply(to_email, subject, body_text):
    """Client ko response email bhejta hai."""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = to_email
        msg['Subject'] = f"Re: {subject}" if not subject.lower().startswith("re:") else subject
        
        msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to_email, msg.as_string())
        server.quit()
        print(f"[✔] GLOBAL SUCCESS: Auto-Reply sent to {to_email}")
    except Exception as e:
        print(f"[!] Email Send Error: {e}")

def check_and_reply_global_inbox():
    """Unread inbox check karke client replies par auto-response bhejta hai."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # Search UNSEEN emails
        status, response = mail.search(None, 'UNSEEN')
        email_ids = response[0].split()

        if not email_ids:
            print("[i] Global Auto-Reply Check: No new client responses.")
            return

        # Latest 5 unread emails process honge
        recent_email_ids = email_ids[-5:]
        print(f"[i] Processing latest unread emails...")

        for e_id in recent_email_ids:
            _, msg_data = mail.fetch(e_id, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    sender = msg.get("From")
                    subject = msg.get("Subject") or "Inquiry"
                    
                    if "<" in sender:
                        sender_email = sender.split("<")[1].replace(">", "").strip()
                    else:
                        sender_email = sender.strip()

                    # Skip Automated/Promotional Emails
                    if any(ignore in sender_email.lower() for ignore in ["no-reply", "noreply", "google", "newsletter", "alert"]):
                        print(f"[i] Ignored promotional email from: {sender_email}")
                        mail.store(e_id, '+FLAGS', '\\Seen')
                        continue

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                break
                    else:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')

                    print(f"\n[🌍] Client Email From: {sender_email}")
                    
                    ai_reply = get_global_ai_reply(body)
                    
                    if ai_reply:
                        send_email_reply(sender_email, subject, ai_reply)
                        mail.store(e_id, '+FLAGS', '\\Seen')

        mail.logout()
    except Exception as e:
        print(f"[!] IMAP Connection Error: {e}")

if __name__ == "__main__":
    print("==================================================")
    print("Kuldeep Brothers AI Studio - Global Auto-Reply AI")
    print("==================================================")
    check_and_reply_global_inbox()
