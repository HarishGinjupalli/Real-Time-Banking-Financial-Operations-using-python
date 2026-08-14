"""
customer_analysis.py
---------------------
This file has functions for customer and account level
analytics - things like "who are our most active customers"
and "what does our overall account balance picture look like".

Just like transaction_analysis.py, each function reads data
with Pandas and returns something ready for the dashboard.
"""

import pandas as pd


def load_accounts_with_customers(engine):
    """
    Loads all accounts joined with their customer's name.
    Input: SQLAlchemy engine
    Returns: a Pandas DataFrame
    """
    query = """
        SELECT a.account_id, a.customer_id, c.name AS customer_name,
               a.account_type, a.balance, a.account_status, a.branch_id
        FROM accounts a
        JOIN customers c ON a.customer_id = c.customer_id
    """
    return pd.read_sql(query, engine)


def get_account_summary(accounts_df):
    """
    Calculates high-level account KPIs.
    Input: accounts DataFrame (from load_accounts_with_customers)
    Returns: a dictionary of KPI values
    """
    if accounts_df.empty:
        return {"active_accounts": 0, "active_customers": 0, "total_balance": 0}

    active_df = accounts_df[accounts_df["account_status"] == "ACTIVE"]

    return {
        "active_accounts": len(active_df),
        "active_customers": active_df["customer_id"].nunique(),
        "total_balance": active_df["balance"].sum(),
    }


def get_top_customers_by_activity(transactions_df, accounts_df, top_n=10):
    """
    Finds the customers with the MOST transactions.
    Input: transactions DataFrame, accounts DataFrame, how many to return
    Returns: a DataFrame with columns [customer_name, transaction_count]
    """
    if transactions_df.empty or accounts_df.empty:
        return pd.DataFrame(columns=["customer_name", "transaction_count"])

    # Attach customer_name to each transaction via the account it belongs to
    merged = transactions_df.merge(
        accounts_df[["account_id", "customer_name"]],
        on="account_id", how="left"
    )

    grouped = merged.groupby("customer_name").agg(
        transaction_count=("transaction_id", "count")
    ).reset_index()

    return grouped.sort_values("transaction_count", ascending=False).head(top_n)


def get_top_customers_by_amount(transactions_df, accounts_df, top_n=10):
    """
    Finds the customers with the HIGHEST total successful
    transaction amount.
    Input: transactions DataFrame, accounts DataFrame, how many to return
    Returns: a DataFrame with columns [customer_name, total_amount]
    """
    if transactions_df.empty or accounts_df.empty:
        return pd.DataFrame(columns=["customer_name", "total_amount"])

    successful_df = transactions_df[transactions_df["transaction_status"] == "SUCCESS"]

    merged = successful_df.merge(
        accounts_df[["account_id", "customer_name"]],
        on="account_id", how="left"
    )

    grouped = merged.groupby("customer_name").agg(
        total_amount=("transaction_amount", "sum")
    ).reset_index()

    return grouped.sort_values("total_amount", ascending=False).head(top_n)


def get_average_transaction_per_customer(transactions_df, accounts_df):
    """
    Calculates the average transaction amount for each customer.
    Input: transactions DataFrame, accounts DataFrame
    Returns: a DataFrame with columns [customer_name, average_amount]
    """
    if transactions_df.empty or accounts_df.empty:
        return pd.DataFrame(columns=["customer_name", "average_amount"])

    successful_df = transactions_df[transactions_df["transaction_status"] == "SUCCESS"]

    merged = successful_df.merge(
        accounts_df[["account_id", "customer_name"]],
        on="account_id", how="left"
    )

    grouped = merged.groupby("customer_name").agg(
        average_amount=("transaction_amount", "mean")
    ).reset_index()

    return grouped.sort_values("average_amount", ascending=False)
