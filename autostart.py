import time
import schedule
import subprocess

def run_agency_tasks():
    print("\n[Auto-Pilot] Running Daily Lead Scraping and Cold Emailing...")
    subprocess.run(["python", "run_agency.py"])

def run_inbox_monitor():
    print("\n[Auto-Pilot] Checking inbox for client replies...")
    subprocess.run(["python", "auto_reply.py"])

# Schedules
schedule.every().day.at("09:00").do(run_agency_tasks)
schedule.every(30).minutes.do(run_inbox_monitor)

print("==================================================")
print("Kuldeep Brothers AI Studio - Auto-Pilot Master Bot Active")
print("==================================================")

# Initial check on startup
run_inbox_monitor()

while True:
    schedule.run_pending()
    time.sleep(1)