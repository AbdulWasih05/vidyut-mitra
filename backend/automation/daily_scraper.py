import os
import time
import logging
import re
from datetime import datetime
import threading

import requests
from bs4 import BeautifulSoup
import schedule
from dotenv import load_dotenv

from backend.db import supabase_client
from backend.output import twilio_dispatcher

logger = logging.getLogger(__name__)

MESCOM_RURAL_URL = "https://mescomruralpayment.mesco.in/"

# --- Scraping Logic ---

def scrape_due_amount(rr_number: str) -> float:
    """
    Scrape the MESCOM rural payment portal for a specific RR Number to find the due amount.

    Field names verified against the live form at MESCOM_RURAL_URL:
    - txtConnectionID (the RR/Connection ID input)
    - BtnPayment (the submit button)
    - rbtPaymentOption=1 (required radio: pay full amount)
    The page also requires __VIEWSTATEGENERATOR alongside __VIEWSTATE.

    The "Net Amount Due:" regex is a best-effort match for the response page;
    the actual MESCOM portal may redirect to a separate payment page rather
    than render the amount inline. Treat 0.0 as "not found / no due".
    """
    try:
        session = requests.Session()
        resp = session.get(MESCOM_RURAL_URL, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')

        def _hidden(name: str) -> str:
            tag = soup.find("input", {"name": name})
            return tag["value"] if tag and tag.has_attr("value") else ""

        payload = {
            "__VIEWSTATE":          _hidden("__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": _hidden("__VIEWSTATEGENERATOR"),
            "__EVENTVALIDATION":    _hidden("__EVENTVALIDATION"),
            "txtConnectionID":      rr_number,
            "rbtPaymentOption":     "1",
            "BtnPayment":           "Continue",
        }

        post_resp = session.post(MESCOM_RURAL_URL, data=payload, timeout=15)
        
        # Scrape amount logic
        # For the hackathon, we simulate finding the amount in the HTML
        result_soup = BeautifulSoup(post_resp.text, 'html.parser')
        amount_text = result_soup.text
        
        # Look for "Net Amount Due: 1540" or similar
        match = re.search(r'(?i)(?:total|net|amount)?\s*due[\s:]*(?:Rs\.?|INR|₹)?\s*([\d\.,]+)', amount_text)
        if match:
            due = float(match.group(1).replace(",", ""))
            return due
        
    except Exception as e:
        logger.error(f"Error scraping data for RR Number {rr_number}: {e}")
        
    return 0.0

# --- Automation Pipeline ---

def run_daily_scraping_job():
    """Fetches all users, checks their MESCOM due amount, and dispatches a reminder.

    RR-number resolution prefers ``users.rr_number`` (set explicitly via the
    ACCOUNT command) and falls back to the most recent ``bills.rr_number``
    (extracted from a bill photo). Without the fallback users who have only
    sent bills (no ACCOUNT command) are missed; without the primary lookup
    users who have only run ACCOUNT (no bill yet) are missed.
    """
    logger.info("Starting daily MESCOM bill scraping job...")
    try:
        client = supabase_client.init_client()

        # Pull both the user-level rr_number and any bill-level rr_numbers.
        response = (
            client.table("users")
            .select("id, phone_number, rr_number, bills(rr_number, created_at)")
            .execute()
        )
        users = response.data

        for user in users:
            # 1. Prefer the explicitly-linked ACCOUNT rr_number.
            latest_rr = user.get("rr_number")

            # 2. Fall back to the most recent bill's rr_number.
            if not latest_rr:
                bills = user.get("bills") or []
                bills.sort(key=lambda b: b.get("created_at") or "", reverse=True)
                latest_rr = next(
                    (b["rr_number"] for b in bills if b.get("rr_number")),
                    None,
                )

            if not latest_rr:
                continue

            amount_due = scrape_due_amount(latest_rr)

            if amount_due > 0:
                logger.info(
                    f"User {user['phone_number']} (RR: {latest_rr}) has a due of ₹{amount_due}."
                )

                message = (
                    f"Hi there! ⚡\n\n"
                    f"It looks like your MESCOM account ({latest_rr}) has an outstanding due of *Rs. {amount_due}*.\n\n"
                    f"📸 Reply with a clear photo of your latest bill, and I'll analyze it to see if you can save on your charges!"
                )

                # Dispatch Twilio message. 1-second gap matches the
                # bill-processing rate-limit policy (CLAUDE.md §6).
                twilio_dispatcher.send_text(user["phone_number"], message)
                time.sleep(1.0)

    except Exception as e:
        logger.exception(f"Failed to run daily scraping job: {e}")

# --- Scheduler ---

def start_scheduler():
    """Starts the schedule loop in a background thread."""
    # Example: Run every day at 10:00 AM
    schedule.every().day.at("10:00").do(run_daily_scraping_job)
    
    logger.info("Automation scheduler started. Will run daily at 10:00 AM.")
    
    def loop():
        while True:
            schedule.run_pending()
            time.sleep(60)
            
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    run_daily_scraping_job()
