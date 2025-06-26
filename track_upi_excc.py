import base64
import re
from datetime import datetime
from collections import defaultdict
from bs4 import BeautifulSoup
from sample import get_gmail_service

def extract_upi_debits(cc_due_dates):
    service = get_gmail_service()
    today = datetime.today().date()
    start_date = today.replace(day=1)

    # Step 1: Find the latest due date from all credit cards
    latest_due_date = max(datetime.strptime(d, '%Y-%m-%d').date() for d in cc_due_dates)

    # Step 2: Decide the range
    if today <= latest_due_date:
        end_date = today
        note = f"UPI transactions shown till today ({end_date})"
    else:
        end_date = latest_due_date
        note = f"UPI transactions shown only till the last credit card due date ({end_date})"

    # Step 3: Gmail Query
    query = f'subject:"You have done a UPI txn" after:{start_date.strftime("%Y/%m/%d")} before:{end_date.strftime("%Y/%m/%d")}'
    results = service.users().messages().list(userId='me', q=query, maxResults=500).execute()
    messages = results.get('messages', [])

    excluded_keywords = ['credit card', 'card payment', 'billdesk', 'visa', 'rupay', 'ending', 'your card', 'billpay']
    daily_spend = defaultdict(float)

    for msg_meta in messages:
        msg = service.users().messages().get(userId='me', id=msg_meta['id']).execute()
        data = msg['payload'].get('body', {}).get('data')
        if not data:
            parts = msg['payload'].get('parts', [])
            for part in parts:
                if part['mimeType'] in ['text/plain', 'text/html']:
                    data = part['body'].get('data')
                    if data:
                        break
        if not data:
            continue

        try:
            data += '=' * (-len(data) % 4)
            html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)

            if any(k in text.lower() for k in excluded_keywords):
                continue

            amount_match = re.search(r'Rs\.? ?([0-9,]+\.\d{2})', text)
            date_match = re.search(r'on (\d{2}-\d{2}-\d{2})', text)
            if amount_match and date_match:
                amount = float(amount_match.group(1).replace(',', ''))
                txn_date = datetime.strptime(date_match.group(1), '%d-%m-%y').strftime('%Y-%m-%d')
                daily_spend[txn_date] += amount
        except Exception as e:
            print(f"⚠️ Error processing a message: {e}")
            continue

    total_spend = sum(daily_spend.values())

    print(f"\n📊 {note}:\n")
    if daily_spend:
        for date in sorted(daily_spend.keys()):
            print(f"📅 {date}: ₹{daily_spend[date]:,.2f}")
        print(f"\n💸 Total UPI Spend: ₹{total_spend:,.2f}")
    else:
        print("ℹ️ No UPI transactions found in this date range.")

    return daily_spend, total_spend

# Example usage:
if __name__ == '__main__':
    cc_due_dates = ["2025-06-24", "2025-06-28", "2025-06-30"]  # Replace with your actual ones
    extract_upi_debits(cc_due_dates)
