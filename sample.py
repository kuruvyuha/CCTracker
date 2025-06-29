import base64
import os
import re
import streamlit as st
from datetime import datetime
from bs4 import BeautifulSoup
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from urllib.parse import urlparse, parse_qs

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None

    # ✅ Load from session_state if available
    if 'creds' in st.session_state:
        creds = st.session_state['creds']

    if not creds:
        if st.secrets.get("streamlit_app") == "1":
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": st.secrets["google_auth"]["client_id"],
                        "client_secret": st.secrets["google_auth"]["client_secret"],
                        "redirect_uris": st.secrets["google_auth"]["redirect_uris"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                },
                scopes=SCOPES,
                redirect_uri=st.secrets["google_auth"]["redirect_uris"][0]
            )

            auth_url, _ = flow.authorization_url(prompt='consent')
            st.markdown(f"[👉 Click here to authorize Gmail access]({auth_url})")

            query_params = st.query_params
            if "code" not in query_params:
                st.info("🔄 Waiting for you to complete Gmail authentication...")
                st.stop()

            code = query_params["code"][0]
            flow.fetch_token(code=code)
            creds = flow.credentials
            st.session_state['creds'] = creds  # ✅ Cache creds for session

    if creds:
        creds = creds.with_quota_project(None)
        return build('gmail', 'v1', credentials=creds)
    else:
        st.stop()

def extract_amount_and_due_date(text):
    amount_match = re.search(
        r'Total\s+(amount|Amount)\s+due.*?[\₹Rs\. ]*([0-9,]+\.\d{2})', 
        text, re.IGNORECASE
    )
    date_match = re.search(
        r'Payment\s+due\s+date.*?(\d{2}[-/]\d{2}[-/]\d{4})', 
        text, re.IGNORECASE
    )
    if not date_match:
        date_match = re.search(r'(\d{2}[-/]\d{2}[-/]\d{4})', text)

    amount = float(amount_match.group(2).replace(',', '')) if amount_match else None
    due_date = datetime.strptime(date_match.group(1), '%d-%m-%Y') if date_match else None
    return amount, due_date

def extract_text_from_message(msg):
    data = msg['payload'].get('body', {}).get('data')
    if not data:
        parts = msg['payload'].get('parts', [])
        for part in parts:
            if part['mimeType'] in ['text/plain', 'text/html']:
                data = part['body'].get('data')
                if data:
                    break
    if data:
        data += '=' * (-len(data) % 4)
        html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        return BeautifulSoup(html, 'html.parser').get_text(separator=' ', strip=True)
    return ""

def get_credit_card_bills():
    service = get_gmail_service()
    query = 'subject:("Credit Card Statement") newer_than:60d'
    response = service.users().messages().list(userId='me', q=query, maxResults=20).execute()
    messages = response.get('messages', [])

    results = {}

    for msg_metadata in messages:
        msg = service.users().messages().get(userId='me', id=msg_metadata['id']).execute()
        text = extract_text_from_message(msg)

        subject = ""
        for header in msg['payload']['headers']:
            if header['name'].lower() == 'subject':
                subject = header['value']
                break

        if "Diners Club International Credit Card Statement" in subject:
            card_name = "Diners Club"
        elif "HDFC BANK UPI RuPay Credit Card Statement" in subject:
            card_name = "RuPay Card"
        elif "HDFC Bank Pixel Credit Card Statement" in subject:
            card_name = "Pixel Card"
        else:
            continue

        amount, due_date = extract_amount_and_due_date(text)
        if amount and due_date:
            if (card_name not in results) or (due_date > datetime.strptime(results[card_name]['due_date'], '%Y-%m-%d')):
                results[card_name] = {
                    "name": card_name,
                    "due_amount": amount,
                    "due_date": due_date.strftime('%Y-%m-%d')
                }

    return list(results.values())

def print_authenticated_user():
    service = get_gmail_service()
    profile = service.users().getProfile(userId='me').execute()
    print(f"\n📧 Gmail account in use: {profile.get('emailAddress')}")

def get_authenticated_email():
    try:
        service = get_gmail_service()
        profile = service.users().getProfile(userId='me').execute()
        return profile.get('emailAddress')
    except Exception as e:
        import traceback
        st.error("❌ Gmail authentication failed.")
        st.exception(e)
        raise

def main():
    print_authenticated_user()
    bills = get_credit_card_bills()

    if not bills:
        print("❌ No credit card bills found.")
    else:
        print("\n📬 Credit Card Bills Found:\n")
        for card in bills:
            print(f"💳 {card['name']}: ₹{card['due_amount']:,.2f} due on {card['due_date']}")

if __name__ == '__main__':
    main()
