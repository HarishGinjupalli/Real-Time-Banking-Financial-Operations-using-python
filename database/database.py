"""
database.py
------------
This file has ONE job: connect Python to our SQL Server database
(the one running inside SQL Server / SSMS on your machine).

We give TWO ways to connect, because different parts of the
project need different tools:

1. get_db_connection()  -> uses pyodbc.
   We use this when we want to INSERT or UPDATE data
   (for example, adding a new transaction).

2. get_engine()         -> uses SQLAlchemy (built on top of pyodbc).
   Pandas works best with SQLAlchemy when READING data
   (for example, pulling transactions into a DataFrame
   for analytics and charts).

All the connection details (server name, database name, etc.)
are stored in the .env file, NOT written directly in the code.

IMPORTANT: pyodbc needs the "ODBC Driver for SQL Server" to be
installed on your Windows machine. If you have SSMS installed,
you almost certainly already have it. You can double check by
opening "ODBC Data Sources (64-bit)" from the Windows Start Menu
and looking under the "Drivers" tab for something like
"ODBC Driver 17 for SQL Server" or "ODBC Driver 18 for SQL Server".
"""

import os
import urllib.parse

import pyodbc
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load the variables from the .env file into the environment
load_dotenv()

# Read each database setting from the environment
DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_NAME = os.getenv("DB_NAME", "banking_analytics")
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")

# DB_AUTH can be "windows" (use your Windows login - the SSMS default)
# or "sql" (use a SQL Server username/password you created)
DB_AUTH = os.getenv("DB_AUTH", "windows")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")


def _build_odbc_connection_string():
    """
    Builds the raw ODBC connection string used by pyodbc.

    If DB_AUTH is "windows", we connect using your current
    Windows login (this is what SSMS uses by default when it
    opens without asking for a username/password).

    If DB_AUTH is "sql", we connect using a SQL Server username
    and password instead (SQL Server Authentication).
    """
    if DB_AUTH.lower() == "windows":
        return (
            f"DRIVER={{{DB_DRIVER}}};"
            f"SERVER={DB_SERVER};"
            f"DATABASE={DB_NAME};"
            f"Trusted_Connection=yes;"
        )
    else:
        return (
            f"DRIVER={{{DB_DRIVER}}};"
            f"SERVER={DB_SERVER};"
            f"DATABASE={DB_NAME};"
            f"UID={DB_USER};"
            f"PWD={DB_PASSWORD};"
        )


def get_db_connection():
    """
    Creates and returns a pyodbc connection.

    Input: none
    Returns: a live SQL Server connection object.

    Use this connection for writing data (INSERT/UPDATE),
    such as adding a new transaction or updating a balance.

    Remember to close the connection when you are done with it
    (connection.close()).
    """
    conn_str = _build_odbc_connection_string()
    connection = pyodbc.connect(conn_str)
    return connection


def get_engine():
    """
    Creates and returns a SQLAlchemy engine for SQL Server.

    Input: none
    Returns: a SQLAlchemy engine object.

    Use this engine for reading data with pandas, for example:
        df = pd.read_sql("SELECT * FROM transactions", engine)
    """
    conn_str = _build_odbc_connection_string()
    # SQLAlchemy needs the raw ODBC string URL-encoded
    quoted_conn_str = urllib.parse.quote_plus(conn_str)
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={quoted_conn_str}")
    return engine


def insert_and_get_id(cursor, sql, params):
    """
    Runs an INSERT statement and returns the new row's identity
    (auto-generated primary key) value.

    SQL Server does not have a simple "cursor.lastrowid" like
    some other databases, so instead we ask SQL Server for
    "SCOPE_IDENTITY()" - the last identity value generated in
    our own session.

    IMPORTANT: we run the INSERT and the SCOPE_IDENTITY() lookup
    as ONE combined statement (separated by a semicolon), not as
    two separate cursor.execute() calls. Running them separately
    can be unreliable with pyodbc - it can lose track of which
    result belongs to which statement and silently return nothing.
    Combining them into a single batch avoids that problem.

    Input:
        cursor - an open pyodbc cursor
        sql    - the INSERT statement, using ? placeholders
        params - a tuple of values matching the ? placeholders

    Returns: the new row's ID as an integer
    """
    combined_sql = f"{sql}; SELECT SCOPE_IDENTITY();"
    cursor.execute(combined_sql, params)

    # The INSERT itself doesn't produce a result set, so we need to
    # explicitly move past it to reach the SELECT SCOPE_IDENTITY()
    # result. Without this, pyodbc raises "No results" because it's
    # still pointed at the INSERT's (empty) result.
    while cursor.description is None:
        cursor.nextset()

    row = cursor.fetchone()
    return int(row[0]) if row and row[0] is not None else None


if __name__ == "__main__":
    # This block only runs if you execute this file directly.
    # It's a simple way to test that the connection works.
    # Run:  python database/database.py
    try:
        conn = get_db_connection()
        print("Connected to SQL Server successfully!")
        conn.close()
    except Exception as error:
        print("Connection failed. Error details below:")
        print(error)