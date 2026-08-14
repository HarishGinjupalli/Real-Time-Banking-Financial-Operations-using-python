"""
sample_data.py
--------------
This script fills our EMPTY database with realistic starter data:

- A few bank branches
- A set of customers
- A bank account for each customer (some customers get 2 accounts)
- A few loans for some customers

We need this "starting data" before we can generate live
transactions, because every transaction must belong to an
existing account.

Run this file ONCE after creating the database tables:
    python data/sample_data.py

Running it again will add duplicate data, so only run it once
(or clear the tables first if you want to start fresh).
"""

import sys
import os
import random
from datetime import date, timedelta

# Add the project's root folder to Python's search path so we
# can import the database connection helper from the
# "database" folder.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.database import get_db_connection, insert_and_get_id

# ---------------------------------------------------------
# Sample reference data used to build fake customers/branches
# ---------------------------------------------------------
FIRST_NAMES = ["Aarav", "Vivaan", "Aditya", "Ishaan", "Sai", "Ananya",
               "Diya", "Priya", "Meera", "Kavya", "Rohan", "Karthik",
               "Sneha", "Pooja", "Arjun", "Neha", "Rahul", "Divya",
               "Amit", "Sanya"]
LAST_NAMES = ["Sharma", "Reddy", "Patel", "Gupta", "Iyer", "Nair",
              "Rao", "Verma", "Menon", "Singh"]
CITIES_STATES = [
    ("Hyderabad", "Telangana"),
    ("Bengaluru", "Karnataka"),
    ("Chennai", "Tamil Nadu"),
    ("Mumbai", "Maharashtra"),
    ("Pune", "Maharashtra"),
    ("Delhi", "Delhi"),
]
CUSTOMER_TYPES = ["INDIVIDUAL", "INDIVIDUAL", "INDIVIDUAL", "BUSINESS"]
ACCOUNT_TYPES = ["SAVINGS", "SAVINGS", "SAVINGS", "CURRENT"]
LOAN_TYPES = ["HOME", "CAR", "PERSONAL", "EDUCATION"]


def insert_branches(cursor):
    """
    Inserts a small list of bank branches.
    Input: a pyodbc cursor
    Returns: a list of the branch_ids that were created
    """
    branches = [
        ("Hyderabad Main Branch", "Hyderabad", "Telangana"),
        ("Bengaluru City Branch", "Bengaluru", "Karnataka"),
        ("Chennai Central Branch", "Chennai", "Tamil Nadu"),
        ("Mumbai Fort Branch", "Mumbai", "Maharashtra"),
        ("Pune Camp Branch", "Pune", "Maharashtra"),
    ]

    branch_ids = []
    for branch_name, city, state in branches:
        new_id = insert_and_get_id(
            cursor,
            "INSERT INTO branches (branch_name, city, state) VALUES (?, ?, ?)",
            (branch_name, city, state)
        )
        branch_ids.append(new_id)

    print(f"Inserted {len(branch_ids)} branches.")
    return branch_ids


def insert_customers(cursor, total_customers=30):
    """
    Inserts a set of fake customers with random but realistic details.
    Input: cursor, and how many customers to create
    Returns: a list of the customer_ids that were created
    """
    customer_ids = []

    for _ in range(total_customers):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        age = random.randint(21, 65)
        gender = random.choice(["Male", "Female"])
        city, state = random.choice(CITIES_STATES)
        customer_type = random.choice(CUSTOMER_TYPES)

        # Account opened sometime in the last 5 years
        days_ago = random.randint(30, 5 * 365)
        account_open_date = date.today() - timedelta(days=days_ago)

        new_id = insert_and_get_id(
            cursor,
            """INSERT INTO customers
               (name, age, gender, city, state, customer_type, account_open_date)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, age, gender, city, state, customer_type, account_open_date)
        )
        customer_ids.append(new_id)

    print(f"Inserted {len(customer_ids)} customers.")
    return customer_ids


def insert_accounts(cursor, customer_ids, branch_ids):
    """
    Gives every customer at least one bank account.
    Some customers (about 30%) get a second account.
    Input: cursor, list of customer_ids, list of branch_ids
    Returns: a list of the account_ids that were created
    """
    account_ids = []

    for customer_id in customer_ids:
        # Every customer gets one account for sure
        num_accounts = 2 if random.random() < 0.3 else 1

        for _ in range(num_accounts):
            branch_id = random.choice(branch_ids)
            account_type = random.choice(ACCOUNT_TYPES)
            # Starting balance somewhere between 5,000 and 200,000 rupees
            starting_balance = round(random.uniform(5000, 200000), 2)

            new_id = insert_and_get_id(
                cursor,
                """INSERT INTO accounts
                   (customer_id, branch_id, account_type, balance, account_status)
                   VALUES (?, ?, ?, ?, 'ACTIVE')""",
                (customer_id, branch_id, account_type, starting_balance)
            )
            account_ids.append(new_id)

    print(f"Inserted {len(account_ids)} accounts.")
    return account_ids


def insert_loans(cursor, customer_ids, num_loans=15):
    """
    Gives a random subset of customers an active loan.
    Input: cursor, list of customer_ids, how many loans to create
    Returns: nothing (loans are not needed elsewhere by id)
    """
    chosen_customers = random.sample(customer_ids, min(num_loans, len(customer_ids)))

    for customer_id in chosen_customers:
        loan_type = random.choice(LOAN_TYPES)
        loan_amount = round(random.uniform(100000, 2000000), 2)
        interest_rate = round(random.uniform(7.0, 14.0), 2)
        # Outstanding amount starts a bit lower than the full loan,
        # to simulate a loan that is already partly repaid
        outstanding_amount = round(loan_amount * random.uniform(0.4, 0.95), 2)
        days_ago = random.randint(60, 3 * 365)
        start_date = date.today() - timedelta(days=days_ago)

        cursor.execute(
            """INSERT INTO loans
               (customer_id, loan_type, loan_amount, interest_rate,
                outstanding_amount, loan_status, start_date)
               VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?)""",
            (customer_id, loan_type, loan_amount, interest_rate,
             outstanding_amount, start_date)
        )

    print(f"Inserted {len(chosen_customers)} loans.")


def main():
    """
    Runs all the insert functions in the correct order and
    commits everything to the database.
    """
    connection = get_db_connection()
    cursor = connection.cursor()

    branch_ids = insert_branches(cursor)
    customer_ids = insert_customers(cursor, total_customers=30)
    insert_accounts(cursor, customer_ids, branch_ids)
    insert_loans(cursor, customer_ids, num_loans=15)

    # Save all the changes to the database
    connection.commit()

    cursor.close()
    connection.close()
    print("Sample data setup complete!")


if __name__ == "__main__":
    main()
