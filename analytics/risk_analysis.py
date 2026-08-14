"""
risk_analysis.py
-----------------
This file contains our SIMPLE, RULE-BASED suspicious
transaction checker.

IMPORTANT: This is NOT a real bank fraud detection system.
Real banks use much more advanced tools. Here we are only
using simple, easy-to-understand rules to demonstrate how
risk scoring works, for learning purposes.

We check each new transaction against 4 simple rules:

Rule 1 - Large amount:
    If the transaction is bigger than 100,000, that's risky
    on its own (someone moving a lot of money at once).

Rule 2 - Many transactions quickly:
    If the same account makes many transactions in a short
    time window (e.g. 10 transactions in 2 minutes), that's
    unusual behaviour.

Rule 3 - Repeated failures:
    If the same account has several FAILED transactions in a
    row recently, that could mean someone is trying random
    amounts/PINs (or a card issue).

Rule 4 - Big withdrawal right after a big deposit:
    If a lot of money was deposited and then quickly pulled
    back out, that is a classic "money laundering" style
    pattern worth flagging.

Each rule adds points to a risk_score (0 to 100).
    0-30   = LOW risk
    31-70  = MEDIUM risk
    71-100 = HIGH risk

If the total score is above 0, we save an alert into the
suspicious_transactions table.
"""

from datetime import datetime, timedelta

# ---------------------------------------------------------
# Rule settings (easy to tweak later)
# ---------------------------------------------------------
LARGE_AMOUNT_THRESHOLD = 100000       # Rule 1
LARGE_AMOUNT_SCORE = 40

RAPID_TXN_WINDOW_MINUTES = 2          # Rule 2
RAPID_TXN_COUNT_THRESHOLD = 5
RAPID_TXN_SCORE = 25

FAILED_TXN_WINDOW_MINUTES = 10        # Rule 3
FAILED_TXN_COUNT_THRESHOLD = 3
FAILED_TXN_SCORE = 20

DEPOSIT_WITHDRAW_WINDOW_MINUTES = 15  # Rule 4
DEPOSIT_WITHDRAW_SCORE = 35


def check_large_amount(amount):
    """
    Rule 1: Flags transactions above the large-amount threshold.
    Input: transaction amount (number)
    Returns: (score, reason_text or None)
    """
    if amount > LARGE_AMOUNT_THRESHOLD:
        return LARGE_AMOUNT_SCORE, "Large transaction amount"
    return 0, None


def check_rapid_transactions(cursor, account_id):
    """
    Rule 2: Flags an account making too many transactions in a
    short time window.
    Input: cursor, account_id
    Returns: (score, reason_text or None)
    """
    window_start = datetime.now() - timedelta(minutes=RAPID_TXN_WINDOW_MINUTES)

    cursor.execute(
        """SELECT COUNT(*) FROM transactions
           WHERE account_id = ? AND transaction_timestamp >= ?""",
        (account_id, window_start)
    )
    count = cursor.fetchone()[0]

    if count >= RAPID_TXN_COUNT_THRESHOLD:
        return RAPID_TXN_SCORE, "Too many transactions in a short time"
    return 0, None


def check_repeated_failures(cursor, account_id):
    """
    Rule 3: Flags an account with several recent failed
    transactions in a row.
    Input: cursor, account_id
    Returns: (score, reason_text or None)
    """
    window_start = datetime.now() - timedelta(minutes=FAILED_TXN_WINDOW_MINUTES)

    cursor.execute(
        """SELECT COUNT(*) FROM transactions
           WHERE account_id = ? AND transaction_status = 'FAILED'
           AND transaction_timestamp >= ?""",
        (account_id, window_start)
    )
    count = cursor.fetchone()[0]

    if count >= FAILED_TXN_COUNT_THRESHOLD:
        return FAILED_TXN_SCORE, "Multiple failed transactions recently"
    return 0, None


def check_deposit_then_withdrawal(cursor, account_id):
    """
    Rule 4: Flags a big withdrawal that happens shortly after a
    big deposit on the same account.
    Input: cursor, account_id
    Returns: (score, reason_text or None)
    """
    window_start = datetime.now() - timedelta(minutes=DEPOSIT_WITHDRAW_WINDOW_MINUTES)

    cursor.execute(
        """SELECT COUNT(*) FROM transactions
           WHERE account_id = ? AND transaction_type = 'DEPOSIT'
           AND transaction_amount > ? AND transaction_timestamp >= ?""",
        (account_id, LARGE_AMOUNT_THRESHOLD / 2, window_start)
    )
    recent_large_deposit = cursor.fetchone()[0]

    cursor.execute(
        """SELECT COUNT(*) FROM transactions
           WHERE account_id = ?
           AND transaction_type IN ('WITHDRAWAL', 'ATM')
           AND transaction_amount > ? AND transaction_timestamp >= ?""",
        (account_id, LARGE_AMOUNT_THRESHOLD / 2, window_start)
    )
    recent_large_withdrawal = cursor.fetchone()[0]

    if recent_large_deposit > 0 and recent_large_withdrawal > 0:
        return DEPOSIT_WITHDRAW_SCORE, "Large withdrawal shortly after large deposit"
    return 0, None


def get_risk_level(score):
    """
    Converts a numeric risk score into a simple risk level label.
    Input: score (0-100)
    Returns: "LOW", "MEDIUM", or "HIGH"
    """
    if score <= 30:
        return "LOW"
    elif score <= 70:
        return "MEDIUM"
    else:
        return "HIGH"


def evaluate_transaction(cursor, transaction_id, account_id, amount):
    """
    Runs ALL 4 rules against one transaction and, if the
    combined score is above 0, saves an alert into the
    suspicious_transactions table.

    Input:
        cursor         - MySQL cursor (same connection used to
                          insert the transaction, so it can see it)
        transaction_id - id of the transaction just created
        account_id     - account the transaction belongs to
        amount         - transaction amount

    Returns: the risk_score (int) that was calculated, so the
             calling code can print/log it if it wants to.
    """
    total_score = 0
    reasons = []

    # Run each rule and collect its score + reason
    for score, reason in [
        check_large_amount(amount),
        check_rapid_transactions(cursor, account_id),
        check_repeated_failures(cursor, account_id),
        check_deposit_then_withdrawal(cursor, account_id),
    ]:
        if score > 0:
            total_score += score
            reasons.append(reason)

    # Cap the score at 100 (in case multiple rules fire at once)
    total_score = min(total_score, 100)

    # Only save an alert if at least one rule was triggered
    if total_score > 0:
        risk_level = get_risk_level(total_score)
        alert_type = "; ".join(reasons)

        cursor.execute(
            """INSERT INTO suspicious_transactions
               (transaction_id, alert_type, risk_score, risk_level, alert_status)
               VALUES (?, ?, ?, ?, 'OPEN')""",
            (transaction_id, alert_type, total_score, risk_level)
        )

    return total_score
