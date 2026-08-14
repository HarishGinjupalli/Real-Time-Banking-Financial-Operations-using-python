"""
app.py
------
This is our Streamlit DASHBOARD - the visual front-end of the
whole project.

It connects to SQL Server, pulls the latest data with Pandas,
and displays KPI cards + Plotly charts. Then it automatically
refreshes itself every few seconds so you can watch new
transactions (created by transaction_generator.py) show up
live.

Run this with:
    streamlit run dashboard/app.py

Make sure transaction_generator.py is ALSO running in another
terminal, otherwise the data will just sit still.

NOTE ON "refresh_count":
Because this dashboard refreshes itself using a "while True"
loop instead of Streamlit's normal rerun mechanism, the same
charts and tables get redrawn over and over inside the SAME
script run. Streamlit gives every chart/table an automatic ID
based on its type and settings, and it does not expect to see
the same one twice in one run - so without help, it throws a
"DuplicateElementId" error on the second loop.

The fix: we pass a "refresh_count" number (which goes up by 1
every loop) into every chart/table's "key" argument, so each
redraw gets its own unique ID, e.g. "trend_chart_3", "trend_chart_4".
"""

import sys
import os
import time

import streamlit as st
import pandas as pd
import plotly.express as px

# Add the project root folder to the path so we can import our
# own database and analytics modules from their folders.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import get_engine
from analytics.transaction_analysis import (
    load_transactions, get_transaction_kpis, get_banking_kpis,
    get_transactions_by_type, get_transactions_by_channel,
    get_transactions_by_branch, get_status_breakdown,
    get_transactions_over_time,
)
from analytics.customer_analysis import (
    load_accounts_with_customers, get_account_summary,
    get_top_customers_by_activity, get_top_customers_by_amount,
)

# ---------------------------------------------------------
# Basic page setup
# ---------------------------------------------------------
st.set_page_config(
    page_title="Real-Time Banking Analytics",
    layout="wide"
)

REFRESH_SECONDS = 4  # how often the dashboard refreshes itself


def load_all_data(engine):
    """
    Pulls everything we need from SQL Server in one place.
    Input: SQLAlchemy engine
    Returns: a dictionary containing all the DataFrames we need
    """
    transactions_df = load_transactions(engine, limit=2000)
    accounts_df = load_accounts_with_customers(engine)

    loans_df = pd.read_sql("SELECT * FROM loans", engine)
    loan_payments_df = pd.read_sql("SELECT * FROM loan_payments", engine)
    suspicious_df = pd.read_sql(
        """SELECT TOP 50 s.*, t.transaction_amount, t.transaction_type, t.account_id
           FROM suspicious_transactions s
           JOIN transactions t ON s.transaction_id = t.transaction_id
           ORDER BY s.created_at DESC""",
        engine
    )

    return {
        "transactions": transactions_df,
        "accounts": accounts_df,
        "loans": loans_df,
        "loan_payments": loan_payments_df,
        "suspicious": suspicious_df,
    }


def render_kpi_cards(data):
    """Draws the top row(s) of KPI number cards. (Metrics don't need keys.)"""
    txn_kpis = get_transaction_kpis(data["transactions"])
    bank_kpis = get_banking_kpis(data["transactions"])
    account_summary = get_account_summary(data["accounts"])

    row1 = st.columns(4)
    row1[0].metric("Total Transactions", f"{txn_kpis['total_transactions']:,}")
    row1[1].metric("Total Transaction Value", f"Rs.{txn_kpis['total_amount']:,.0f}")
    row1[2].metric("Active Customers", f"{account_summary['active_customers']:,}")
    row1[3].metric("Active Accounts", f"{account_summary['active_accounts']:,}")

    row2 = st.columns(4)
    row2[0].metric("Total Deposits", f"Rs.{bank_kpis['total_deposits']:,.0f}")
    row2[1].metric("Total Withdrawals", f"Rs.{bank_kpis['total_withdrawals']:,.0f}")
    row2[2].metric("Total Transfers", f"Rs.{bank_kpis['total_transfers']:,.0f}")
    row2[3].metric("Suspicious Alerts", f"{len(data['suspicious']):,}")


def render_transaction_charts(data, refresh_count):
    """Draws the transaction trend and breakdown charts."""
    st.subheader("Transaction Trends")

    trend_df = get_transactions_over_time(data["transactions"], freq="min")
    if not trend_df.empty:
        fig = px.line(trend_df, x="time_bucket", y="count",
                       title="Transactions Per Minute", markers=True)
        st.plotly_chart(fig, use_container_width=True,
                         key=f"trend_chart_{refresh_count}")
    else:
        st.info("No transaction data yet. Start transaction_generator.py.")

    col1, col2, col3 = st.columns(3)

    with col1:
        type_df = get_transactions_by_type(data["transactions"])
        fig = px.bar(type_df, x="transaction_type", y="count",
                      title="Transactions by Type")
        st.plotly_chart(fig, use_container_width=True,
                         key=f"type_chart_{refresh_count}")

    with col2:
        channel_df = get_transactions_by_channel(data["transactions"])
        fig = px.bar(channel_df, x="transaction_channel", y="count",
                      title="Transactions by Channel")
        st.plotly_chart(fig, use_container_width=True,
                         key=f"channel_chart_{refresh_count}")

    with col3:
        status_df = get_status_breakdown(data["transactions"])
        fig = px.pie(status_df, names="transaction_status", values="count",
                      title="Success vs Failed vs Pending")
        st.plotly_chart(fig, use_container_width=True,
                         key=f"status_chart_{refresh_count}")


def render_branch_charts(data, refresh_count):
    """Draws branch-level charts."""
    st.subheader("Branch Analytics")

    branch_df = get_transactions_by_branch(data["transactions"])
    if branch_df.empty:
        st.info("No branch data yet.")
        return

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(branch_df, x="branch_id", y="count",
                      title="Transactions by Branch")
        st.plotly_chart(fig, use_container_width=True,
                         key=f"branch_count_chart_{refresh_count}")
    with col2:
        fig = px.bar(branch_df, x="branch_id", y="total_amount",
                      title="Transaction Amount by Branch")
        st.plotly_chart(fig, use_container_width=True,
                         key=f"branch_amount_chart_{refresh_count}")


def render_customer_section(data, refresh_count):
    """Draws the top customers tables."""
    st.subheader("Customer Analytics")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Top 10 Most Active Customers**")
        active_df = get_top_customers_by_activity(data["transactions"], data["accounts"])
        st.dataframe(active_df, use_container_width=True, hide_index=True,
                     key=f"active_customers_table_{refresh_count}")

    with col2:
        st.markdown("**Top 10 Customers by Transaction Value**")
        amount_df = get_top_customers_by_amount(data["transactions"], data["accounts"])
        st.dataframe(amount_df, use_container_width=True, hide_index=True,
                     key=f"top_amount_customers_table_{refresh_count}")


def render_risk_section(data, refresh_count):
    """Draws the suspicious transaction / risk panel."""
    st.subheader("Risk & Suspicious Transaction Analytics")

    suspicious_df = data["suspicious"]

    if suspicious_df.empty:
        st.success("No suspicious transactions flagged yet.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Alerts", len(suspicious_df))
    col2.metric("High Risk", len(suspicious_df[suspicious_df["risk_level"] == "HIGH"]))
    col3.metric("Medium Risk", len(suspicious_df[suspicious_df["risk_level"] == "MEDIUM"]))

    st.markdown("**Most Recent Alerts**")
    display_cols = ["alert_id", "transaction_id", "account_id", "transaction_type",
                     "transaction_amount", "alert_type", "risk_score", "risk_level",
                     "created_at"]
    st.dataframe(suspicious_df[display_cols], use_container_width=True, hide_index=True,
                 key=f"suspicious_table_{refresh_count}")


def render_loan_section(data, refresh_count):
    """Draws the loan analytics panel."""
    st.subheader("Loan Analytics")

    loans_df = data["loans"]
    payments_df = data["loan_payments"]

    if loans_df.empty:
        st.info("No loan data yet.")
        return

    total_loans = len(loans_df)
    total_loan_amount = loans_df["loan_amount"].sum()
    outstanding_amount = loans_df["outstanding_amount"].sum()
    total_payments = payments_df["payment_amount"].sum() if not payments_df.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Loans", f"{total_loans:,}")
    col2.metric("Total Loan Amount", f"Rs.{total_loan_amount:,.0f}")
    col3.metric("Outstanding Amount", f"Rs.{outstanding_amount:,.0f}")
    col4.metric("Total Repayments Made", f"Rs.{total_payments:,.0f}")

    loan_type_df = loans_df.groupby("loan_type").agg(
        count=("loan_id", "count"),
        total_amount=("loan_amount", "sum")
    ).reset_index()
    fig = px.bar(loan_type_df, x="loan_type", y="total_amount",
                  title="Loan Amount by Loan Type")
    st.plotly_chart(fig, use_container_width=True,
                     key=f"loan_type_chart_{refresh_count}")


def main():
    """Builds the full dashboard page and refreshes it in a loop."""
    st.title("Real-Time Banking Financial Operations Dashboard")
    st.caption("All data shown is simulated for learning/demo purposes only.")

    engine = get_engine()

    # A placeholder lets us redraw the whole dashboard in the same
    # spot on the page each time, instead of stacking copies below
    # each other.
    placeholder = st.empty()

    # This number goes up by 1 every loop and gets baked into every
    # chart/table's key, so Streamlit never sees two elements with
    # the exact same ID.
    refresh_count = 0

    while True:
        data = load_all_data(engine)

        with placeholder.container():
            render_kpi_cards(data)
            st.divider()
            render_transaction_charts(data, refresh_count)
            st.divider()
            render_branch_charts(data, refresh_count)
            st.divider()
            render_customer_section(data, refresh_count)
            st.divider()
            render_risk_section(data, refresh_count)
            st.divider()
            render_loan_section(data, refresh_count)
            st.caption(f"Last updated: {pd.Timestamp.now().strftime('%H:%M:%S')} "
                       f"(auto-refreshes every {REFRESH_SECONDS}s)")

        refresh_count += 1
        time.sleep(REFRESH_SECONDS)


if __name__ == "__main__":
    main()