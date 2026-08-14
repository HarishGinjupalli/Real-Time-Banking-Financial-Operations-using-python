"""
transaction_generator.py
-------------------------
This is the script that makes our project feel "real-time".

It runs in a loop, and every few seconds it:
    1. Picks a random existing account
    2. Picks a random transaction type (deposit, withdrawal, etc.)
    3. Decides if it succeeds, fails, or is pending
    4. Updates the account balance correctly
    5. Saves the transaction into SQL Server
    6. Checks the transaction for suspicious activity

Run this file and LEAVE IT RUNNING in its own terminal:
    python transaction_generator.py

While it runs, open the Streamlit dashboard in ANOTHER terminal
to watch the numbers update live.

Press CTRL + C to stop the generator.
"""

import time
import random
from datetime import date

from database.database import get_db_connection, insert_and_get_id
from analytics.risk_analysis import evaluate_transaction

# ---------------------------------------------------------
# Settings that control how transactions are generated
# ---------------------------------------------------------

# How long to wait between each generated transaction (seconds)
MIN_DELAY = 1
MAX_DELAY = 3

# Transaction types and how likely each one is to happen.
# (These don't have to add up to 100, they are just relative weights.)
TRANSACTION_TYPES = ["DEPOSIT", "WITHDRAWAL", "TRANSFER", "ATM",
                      "UPI", "CARD", "LOAN_PAYMENT", "FEE"]
TRANSACTION_WEIGHTS = [20, 20, 10, 15, 20, 10, 3, 2]

# Which channel is used for each transaction type
TYPE_TO_CHANNELS = {
    "DEPOSIT": ["BRANCH", "MOBILE_BANKING"],
    "WITHDRAWAL": ["BRANCH", "ATM"],
    "TRANSFER": ["INTERNET_BANKING", "MOBILE_BANKING"],
    "ATM": ["ATM"],
    "UPI": ["UPI"],
    "CARD": ["DEBIT_CARD", "CREDIT_CARD"],
    "LOAN_PAYMENT": ["INTERNET_BANKING", "MOBILE_BANKING", "BRANCH"],
    "FEE": ["BRANCH", "INTERNET_BANKING"],
}

# Most transactions succeed, a few fail, a very small number stay pending
STATUS_OPTIONS = ["SUCCESS", "SUCCESS", "SUCCESS", "SUCCESS",
                   "SUCCESS", "SUCCESS", "SUCCESS", "SUCCESS",
                   "FAILED", "PENDING"]


def get_random_amount(transaction_type):
    """
    Picks a realistic random amount based on the transaction type.
    Input: transaction_type (string)
    Returns: amount (float, rounded to 2 decimals)
    """
    ranges = {
        "DEPOSIT": (1000, 50000),
        "WITHDRAWAL": (500, 20000),
        "TRANSFER": (500, 100000),
        "ATM": (500, 10000),
        "UPI": (50, 15000),
        "CARD": (100, 30000),
        "LOAN_PAYMENT": (2000, 25000),
        "FEE": (50, 500),
    }
    low, high = ranges.get(transaction_type, (100, 5000))
    return round(random.uniform(low, high), 2)


def fetch_random_account(cursor):
    """
    Picks one random ACTIVE account from the database.

    NOTE: SQL Server doesn't have MySQL's "ORDER BY RAND() LIMIT 1".
    Instead we use "SELECT TOP 1 ... ORDER BY NEWID()", which is
    the standard SQL Server way to get a random row.

    Input: cursor
    Returns: a dict with account_id, customer_id, branch_id, balance
             or None if there are no active accounts
    """
    cursor.execute(
        """SELECT TOP 1 account_id, customer_id, branch_id, balance
           FROM accounts WHERE account_status = 'ACTIVE'
           ORDER BY NEWID()"""
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "account_id": row[0],
        "customer_id": row[1],
        "branch_id": row[2],
        "balance": float(row[3]),
    }


def fetch_random_active_loan(cursor, customer_id):
    """
    Looks for an active loan belonging to a specific customer.
    Input: cursor, customer_id
    Returns: loan_id (int) or None if the customer has no active loan
    """
    cursor.execute(
        """SELECT TOP 1 loan_id FROM loans
           WHERE customer_id = ? AND loan_status = 'ACTIVE'
           ORDER BY NEWID()""",
        (customer_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


def update_balance(cursor, account_id, new_balance):
    """
    Updates the balance of one account.
    Input: cursor, account_id, new_balance
    Returns: nothing
    """
    cursor.execute(
        "UPDATE accounts SET balance = ? WHERE account_id = ?",
        (new_balance, account_id)
    )


def insert_transaction(cursor, account_id, transaction_type, amount,
                        channel, status, branch_id,
                        source_account=None, destination_account=None):
    """
    Inserts one row into the transactions table.
    Input: all the transaction details
    Returns: the new transaction_id
    """
    return insert_and_get_id(
        cursor,
        """INSERT INTO transactions
           (account_id, transaction_type, transaction_amount,
            transaction_channel, transaction_status,
            source_account, destination_account, branch_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (account_id, transaction_type, amount, channel, status,
         source_account, destination_account, branch_id)
    )


def process_deposit(cursor, account):
    """
    Handles a DEPOSIT: money is added to the account.
    Returns: (transaction_type, amount, channel, status)
    """
    amount = get_random_amount("DEPOSIT")
    status = random.choice(STATUS_OPTIONS)
    channel = random.choice(TYPE_TO_CHANNELS["DEPOSIT"])

    if status == "SUCCESS":
        new_balance = account["balance"] + amount
        update_balance(cursor, account["account_id"], new_balance)

    return "DEPOSIT", amount, channel, status


def process_debit_style(cursor, account, transaction_type):
    """
    Handles any transaction that REMOVES money from the account:
    WITHDRAWAL, ATM, UPI, CARD, FEE.

    We only remove the money if the account has enough balance.
    If not, we mark it as FAILED (insufficient funds) instead of
    letting the balance go negative.

    Returns: (transaction_type, amount, channel, status)
    """
    amount = get_random_amount(transaction_type)
    channel = random.choice(TYPE_TO_CHANNELS[transaction_type])

    if amount > account["balance"]:
        # Not enough money - the transaction fails
        status = "FAILED"
    else:
        status = random.choice(STATUS_OPTIONS)
        if status == "SUCCESS":
            new_balance = account["balance"] - amount
            update_balance(cursor, account["account_id"], new_balance)

    return transaction_type, amount, channel, status


def process_transfer(cursor, account):
    """
    Handles a TRANSFER: money moves from this account (source)
    to another random account (destination).

    Returns: (transaction_type, amount, channel, status,
              source_account_id, destination_account_id)
    or None if there was no valid second account to transfer to.
    """
    cursor.execute(
        """SELECT TOP 1 account_id, balance FROM accounts
           WHERE account_status = 'ACTIVE' AND account_id != ?
           ORDER BY NEWID()""",
        (account["account_id"],)
    )
    row = cursor.fetchone()
    if row is None:
        return None

    destination_account_id = row[0]
    amount = get_random_amount("TRANSFER")
    channel = random.choice(TYPE_TO_CHANNELS["TRANSFER"])

    if amount > account["balance"]:
        status = "FAILED"
    else:
        status = random.choice(STATUS_OPTIONS)
        if status == "SUCCESS":
            # Subtract from source account
            new_source_balance = account["balance"] - amount
            update_balance(cursor, account["account_id"], new_source_balance)

            # Add to destination account
            destination_balance = float(row[1])
            new_destination_balance = destination_balance + amount
            update_balance(cursor, destination_account_id, new_destination_balance)

    return "TRANSFER", amount, channel, status, account["account_id"], destination_account_id


def process_loan_payment(cursor, account):
    """
    Handles a LOAN_PAYMENT: money leaves the account and reduces
    the customer's outstanding loan balance.

    If the customer has no active loan, we simply skip this and
    return None (the caller will just try a different transaction
    type next time).

    Returns: (transaction_type, amount, channel, status) or None
    """
    loan_id = fetch_random_active_loan(cursor, account["customer_id"])
    if loan_id is None:
        return None

    amount = get_random_amount("LOAN_PAYMENT")
    channel = random.choice(TYPE_TO_CHANNELS["LOAN_PAYMENT"])

    if amount > account["balance"]:
        status = "FAILED"
    else:
        status = random.choice(STATUS_OPTIONS)
        if status == "SUCCESS":
            new_balance = account["balance"] - amount
            update_balance(cursor, account["account_id"], new_balance)

            # Reduce the outstanding loan amount, but never below 0
            cursor.execute(
                "SELECT outstanding_amount FROM loans WHERE loan_id = ?",
                (loan_id,)
            )
            outstanding = float(cursor.fetchone()[0])
            new_outstanding = max(outstanding - amount, 0)

            cursor.execute(
                "UPDATE loans SET outstanding_amount = ? WHERE loan_id = ?",
                (new_outstanding, loan_id)
            )

            # If the loan is fully paid off, close it
            if new_outstanding == 0:
                cursor.execute(
                    "UPDATE loans SET loan_status = 'CLOSED' WHERE loan_id = ?",
                    (loan_id,)
                )

            # Log this repayment in loan_payments too
            cursor.execute(
                """INSERT INTO loan_payments
                   (loan_id, payment_amount, payment_date, payment_status)
                   VALUES (?, ?, ?, ?)""",
                (loan_id, amount, date.today(), status)
            )

    return "LOAN_PAYMENT", amount, channel, status


def generate_one_transaction(cursor):
    """
    Generates exactly ONE random transaction for a random account,
    saves it to the database, updates balances, and runs the risk
    check on it.

    Returns: nothing (just prints what happened)
    """
    account = fetch_random_account(cursor)
    if account is None:
        print("No active accounts found. Run sample_data.py first.")
        return

    transaction_type = random.choices(TRANSACTION_TYPES, weights=TRANSACTION_WEIGHTS)[0]

    source_account = None
    destination_account = None

    if transaction_type == "DEPOSIT":
        result = process_deposit(cursor, account)
    elif transaction_type == "TRANSFER":
        result = process_transfer(cursor, account)
        if result is None:
            return  # no second account available, skip this round
        transaction_type, amount, channel, status, source_account, destination_account = result
        result = (transaction_type, amount, channel, status)
    elif transaction_type == "LOAN_PAYMENT":
        result = process_loan_payment(cursor, account)
        if result is None:
            return  # this customer has no active loan, skip this round
    else:
        # WITHDRAWAL, ATM, UPI, CARD, FEE all behave the same way
        result = process_debit_style(cursor, account, transaction_type)

    transaction_type, amount, channel, status = result

    transaction_id = insert_transaction(
        cursor, account["account_id"], transaction_type, amount,
        channel, status, account["branch_id"],
        source_account, destination_account
    )

    # Only successful/failed money-moving transactions are worth
    # risk-checking (pending ones haven't really "happened" yet)
    risk_score = evaluate_transaction(
        cursor, transaction_id, account["account_id"], amount
    )

    flag = f" [RISK SCORE: {risk_score}]" if risk_score > 0 else ""
    print(f"{transaction_type:<13} | Rs.{amount:>10,.2f} | {status:<8} | "
          f"account {account['account_id']}{flag}")


def main():
    """
    Keeps generating transactions forever (until you press CTRL+C).
    """
    print("Real-time transaction generator started.")
    print("Press CTRL + C to stop.\n")

    try:
        while True:
            connection = get_db_connection()
            cursor = connection.cursor()

            generate_one_transaction(cursor)

            connection.commit()
            cursor.close()
            connection.close()

            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    except KeyboardInterrupt:
        print("\nTransaction generator stopped.")


if __name__ == "__main__":
    main()
