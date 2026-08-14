"""
transaction_analysis.py
------------------------
This file has functions that pull transaction data out of MySQL
and turn it into useful KPIs (Key Performance Indicators) and
tables using Pandas.

Every function here does the same basic pattern:
    1. Run a SQL query (or read a table) into a Pandas DataFrame
    2. Use Pandas to calculate something useful from it
    3. Return the result so the dashboard can display it

Keeping these functions separate from the dashboard code makes
the project easier to read and test.
"""

import pandas as pd


def load_transactions(engine, limit=1000):
    """
    Loads the most recent transactions into a DataFrame.
    Input: SQLAlchemy engine, how many rows to load
    Returns: a Pandas DataFrame
    """
    # SQL Server uses "SELECT TOP n" instead of "LIMIT n"
    query = f"""
        SELECT TOP {limit} * FROM transactions
        ORDER BY transaction_timestamp DESC
    """
    return pd.read_sql(query, engine)


def get_transaction_kpis(df):
    """
    Calculates the main transaction KPIs from a transactions DataFrame.
    Input: transactions DataFrame (from load_transactions)
    Returns: a dictionary of KPI values
    """
    if df.empty:
        return {
            "total_transactions": 0, "total_amount": 0,
            "successful": 0, "failed": 0, "pending": 0,
            "average_amount": 0, "highest_amount": 0, "lowest_amount": 0,
        }

    successful_df = df[df["transaction_status"] == "SUCCESS"]

    return {
        "total_transactions": len(df),
        "total_amount": successful_df["transaction_amount"].sum(),
        "successful": len(successful_df),
        "failed": len(df[df["transaction_status"] == "FAILED"]),
        "pending": len(df[df["transaction_status"] == "PENDING"]),
        "average_amount": successful_df["transaction_amount"].mean() if not successful_df.empty else 0,
        "highest_amount": successful_df["transaction_amount"].max() if not successful_df.empty else 0,
        "lowest_amount": successful_df["transaction_amount"].min() if not successful_df.empty else 0,
    }


def get_banking_kpis(df):
    """
    Calculates totals for each major transaction type
    (deposits, withdrawals, transfers, loan payments, fees).
    Input: transactions DataFrame
    Returns: a dictionary of totals
    """
    successful_df = df[df["transaction_status"] == "SUCCESS"]

    def total_for(transaction_type):
        subset = successful_df[successful_df["transaction_type"] == transaction_type]
        return subset["transaction_amount"].sum()

    return {
        "total_deposits": total_for("DEPOSIT"),
        "total_withdrawals": total_for("WITHDRAWAL"),
        "total_transfers": total_for("TRANSFER"),
        "total_loan_payments": total_for("LOAN_PAYMENT"),
        "total_fees": total_for("FEE"),
    }


def get_transactions_by_type(df):
    """
    Counts and sums transactions grouped by transaction_type.
    Input: transactions DataFrame
    Returns: a DataFrame with columns [transaction_type, count, total_amount]
    """
    if df.empty:
        return pd.DataFrame(columns=["transaction_type", "count", "total_amount"])

    grouped = df.groupby("transaction_type").agg(
        count=("transaction_id", "count"),
        total_amount=("transaction_amount", "sum")
    ).reset_index()
    return grouped.sort_values("count", ascending=False)


def get_transactions_by_channel(df):
    """
    Counts transactions grouped by channel (ATM, UPI, etc.)
    Input: transactions DataFrame
    Returns: a DataFrame with columns [transaction_channel, count]
    """
    if df.empty:
        return pd.DataFrame(columns=["transaction_channel", "count"])

    grouped = df.groupby("transaction_channel").agg(
        count=("transaction_id", "count")
    ).reset_index()
    return grouped.sort_values("count", ascending=False)


def get_transactions_by_branch(df):
    """
    Summarizes transaction volume and value per branch.
    Input: transactions DataFrame
    Returns: a DataFrame with columns
             [branch_id, count, total_amount, failed_count]
    """
    if df.empty:
        return pd.DataFrame(columns=["branch_id", "count", "total_amount", "failed_count"])

    grouped = df.groupby("branch_id").apply(
        lambda g: pd.Series({
            "count": len(g),
            "total_amount": g[g["transaction_status"] == "SUCCESS"]["transaction_amount"].sum(),
            "failed_count": len(g[g["transaction_status"] == "FAILED"]),
        })
    ).reset_index()
    return grouped.sort_values("count", ascending=False)


def get_status_breakdown(df):
    """
    Counts how many transactions fall into each status
    (SUCCESS, FAILED, PENDING) - useful for a pie/bar chart.
    Input: transactions DataFrame
    Returns: a DataFrame with columns [transaction_status, count]
    """
    if df.empty:
        return pd.DataFrame(columns=["transaction_status", "count"])

    grouped = df.groupby("transaction_status").agg(
        count=("transaction_id", "count")
    ).reset_index()
    return grouped


def get_transactions_over_time(df, freq="min"):
    """
    Groups transactions into time buckets so we can plot a trend line.
    Input: transactions DataFrame, freq ("min" = per minute, "H" = per hour)
    Returns: a DataFrame with columns [time_bucket, count, total_amount]
    """
    if df.empty:
        return pd.DataFrame(columns=["time_bucket", "count", "total_amount"])

    df = df.copy()
    df["transaction_timestamp"] = pd.to_datetime(df["transaction_timestamp"])
    df["time_bucket"] = df["transaction_timestamp"].dt.floor(freq)

    grouped = df.groupby("time_bucket").agg(
        count=("transaction_id", "count"),
        total_amount=("transaction_amount", "sum")
    ).reset_index()
    return grouped.sort_values("time_bucket")
