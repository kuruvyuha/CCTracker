import streamlit as st
import datetime
import streamlit.components.v1 as components
from sample import get_credit_card_bills, get_authenticated_email
from track_upi_excc import extract_upi_debits

st.set_page_config(page_title="CC Tracker", layout="wide")
st.title("\ud83d\udcca Credit Card + UPI Tracker")

# Sidebar Inputs
st.sidebar.header("\ud83d\udd27 Configure")
salary_date = st.sidebar.date_input("Salary Credited On", datetime.date.today())
account_balance = st.sidebar.number_input("Available Bank Balance (₹)", min_value=0.0, format="%.2f")

# Gmail Auth with Visual Tracker
st.sidebar.subheader("\ud83d\udd10 Gmail Authentication Status")
with st.sidebar.status("Checking Gmail authentication...", expanded=True) as status:
    try:
        email = get_authenticated_email()
        st.sidebar.success("\u2705 Gmail authenticated")
        st.sidebar.markdown(f"\ud83d\udce7 Logged in as: `{email}`")
        status.update(label="Gmail authentication complete", state="complete")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        st.sidebar.error("\u274c Gmail authentication failed.")
        st.sidebar.markdown("**Error details:**")
        st.sidebar.code(tb, language="python")

        if "metadata.google.internal" in tb:
            st.sidebar.warning("\u26a0\ufe0f GCP metadata call failed. This often happens on Streamlit Cloud.")

        status.update(label="Gmail authentication failed", state="error")
        st.stop()

# Get credit card bill data
credit_cards = get_credit_card_bills()
if not credit_cards:
    st.error("No credit card statements found.")
    st.stop()

# Extract due dates for UPI tracking logic
due_dates = [card['due_date'] for card in credit_cards]
upi_data, total_upi = extract_upi_debits(due_dates)

total_due = sum(card["due_amount"] for card in credit_cards)
estimated_balance = account_balance - total_upi
net_available = estimated_balance

# Updated Jar color and fill logic based on user-defined thresholds
# PRD logic:
# - Green if net balance > 150% of cumulative due (fill 80%)
# - Amber if net balance between 110% and 150% of due (fill 45%)
# - Red if net balance < 110% of due (fill 10%)

def get_jar_status(net, due):
    if net > 1.5 * due:
        return '#00b894', 'success', 80  # Green
    elif net > 1.1 * due:
        return '#fab005', 'warning', 45  # Amber
    else:
        return '#e03131', 'error', 10   # Red

jar_color, alert_type, jar_fill_level = get_jar_status(net_available, total_due)
fill_pct = 150 - (jar_fill_level / 100) * 150

# Dashboard Metrics
st.subheader("\ud83d\udccc Current Snapshot")
col1, col2, col3 = st.columns(3)
col1.metric("Available Balance", f"₹{account_balance:,.2f}")
col2.metric("Total Credit Card Due", f"₹{total_due:,.2f}")
col3.metric("UPI Expenses", f"₹{total_upi:,.2f}")

# Net Savings
st.subheader("\ud83d\udcbe Amount Left to Pay Credit Card Dues")
if alert_type == 'success':
    st.success(f"You have ₹{net_available:,.2f} left after UPI spending. This is more than enough.")
elif alert_type == 'warning':
    st.warning(f"You have ₹{net_available:,.2f} left after UPI spending. This may be enough but is cutting close.")
else:
    st.error(f"You have only ₹{net_available:,.2f} left after UPI spending. Urgent action needed!")

st.subheader("\ud83e\udee9 Credit Card Jar Status")

jar_html = f"""
<div style="position: relative; width: 200px; height: 300px; margin: auto;">
  <svg viewBox="0 0 100 150" style="width: 100%; height: auto;">
    <defs>
      <linearGradient id="waveGradient" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="{jar_color}" />
        <stop offset="100%" stop-color="{jar_color}" />
      </linearGradient>
      <clipPath id="jarClip">
        <rect x="0" y="0" width="100" height="150" rx="20" ry="20" />
      </clipPath>
    </defs>
    <g clip-path="url(#jarClip)">
      <path id="wave" fill="url(#waveGradient)">
        <animate attributeName="d" dur="4s" repeatCount="indefinite"
          values="
          M0,{fill_pct} Q25,{fill_pct - 5} 50,{fill_pct} T100,{fill_pct} V150 H0 Z;
          M0,{fill_pct} Q25,{fill_pct + 5} 50,{fill_pct} T100,{fill_pct} V150 H0 Z;
          M0,{fill_pct} Q25,{fill_pct - 5} 50,{fill_pct} T100,{fill_pct} V150 H0 Z" />
      </path>
    </g>
    <rect x="0" y="0" width="100" height="150" rx="20" ry="20" fill="none" stroke="#999" stroke-width="2" />
  </svg>
  <div style="text-align: center; font-weight: bold; margin-top: 10px;">₹{net_available:,.2f}</div>
</div>
"""

components.html(jar_html, height=350)

# Credit Card Details
st.subheader("\ud83d\udcb3 Credit Card Details")
for card in credit_cards:
    st.markdown(f"**{card['name']}**")
    st.write(f"- Due Amount: ₹{card['due_amount']:,.2f}")
    st.write(f"- Due Date: {card['due_date']}")
    st.markdown("---")

# UPI Transaction Breakdown
st.subheader("\ud83d\udcb8 UPI Transaction History")
if upi_data:
    for date in sorted(upi_data.keys()):
        st.write(f"\ud83d\uddd5\ufe0f {date}: ₹{upi_data[date]:,.2f}")
else:
    st.info("No UPI transactions found for this month.")

# Tip
st.info("\ud83d\udca1 Tip: Treat your credit card like a savings account. Spend mindfully, clear dues in full, and earn rewards!")
