# Real-Time Banking Financial Operations & Transaction Analytics System

A simulated banking analytics system built with **Python, Microsoft SQL Server (via SSMS), Pandas, and Streamlit**. It continuously generates fake banking transactions, stores them in SQL Server, and displays live-updating KPIs, charts, and a simple rule-based risk/suspicious-transaction detector on a Streamlit dashboard.

> ⚠️ **All data is simulated.** No real customers, accounts, or financial APIs are used. The risk/fraud detection here uses simple, easy-to-understand rules for learning purposes — it is **not** a real bank-grade fraud system.

---

## What This Project Does

```
Python Transaction Generator
        ↓
SQL Server Database (banking_analytics)
        ↓
Python + Pandas Analytics
        ↓
Simple Rule-Based Risk Detection
        ↓
Streamlit + Plotly Dashboard (auto-refreshing)
```

It simulates: deposits, withdrawals, ATM transactions, bank transfers, UPI payments, card transactions, loan payments, and bank fees — across multiple branches and customers — and analyzes them live.

## Tech Stack

| Tool | Purpose |
|---|---|
| Python | Transaction generation, analytics, dashboard |
| Microsoft SQL Server (via SSMS) | Data storage |
| Pandas / NumPy | Data analysis |
| pyodbc | Writing data to SQL Server |
| SQLAlchemy | Reading data into Pandas |
| Plotly | Interactive charts |
| Streamlit | Live dashboard UI |

## Project Structure

```
banking_analytics/
│
├── database/
│   ├── database.py       # SQL Server connection helper (pyodbc + SQLAlchemy)
│   └── schema.sql         # Creates the database and all 7 tables (T-SQL)
│
├── data/
│   └── sample_data.py     # Inserts starter branches, customers, accounts, loans
│
├── analytics/
│   ├── transaction_analysis.py   # Transaction KPIs, charts data
│   ├── customer_analysis.py      # Customer/account KPIs, top customers
│   └── risk_analysis.py          # Rule-based suspicious transaction detector
│
├── dashboard/
│   └── app.py              # Streamlit dashboard (the main UI)
│
├── transaction_generator.py  # Generates live transactions continuously
├── requirements.txt
├── .env                      # Database connection settings (not committed to git)
├── .gitignore
└── README.md
```

## Setup Instructions

### 1. Find your SQL Server instance name
Open **SSMS** and look at the "Server name" box on the connect screen — it's usually one of:
- `localhost` or `.` (default instance)
- `localhost\SQLEXPRESS` (SQL Server Express, most common on personal PCs)

You'll need this exact value for the `.env` file in Step 5.

### 2. Create the database and tables
In SSMS: **File → Open → File...**, open `database/schema.sql`, then click **Execute** (or press `F5`). This creates the `banking_analytics` database and all 7 tables.

### 3. Confirm the ODBC driver is installed
Press the Windows key, search for **"ODBC Data Sources (64-bit)"**, open it, and click the **Drivers** tab. You should see an entry like `ODBC Driver 17 for SQL Server` or `ODBC Driver 18 for SQL Server`. If you have SSMS installed, one of these is almost always already present. Note down the exact name shown — you'll need it in Step 5.

### 4. Set up a Python virtual environment
In VS Code's terminal, from the `banking_analytics` folder:

```bash
python -m venv venv
venv\Scripts\activate
```

### 5. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 6. Configure your `.env` file
Open `.env` and update it to match what you found in Steps 1 and 3:

```
DB_SERVER=localhost\SQLEXPRESS
DB_NAME=banking_analytics
DB_DRIVER=ODBC Driver 17 for SQL Server
DB_AUTH=windows
DB_USER=
DB_PASSWORD=
```

- Leave `DB_AUTH=windows` if SSMS connects for you automatically without asking for a username/password (this is the default — called **Windows Authentication**).
- If your SSMS setup uses **SQL Server Authentication** instead (a login screen asking for a username/password), set `DB_AUTH=sql` and fill in `DB_USER` and `DB_PASSWORD`.

### 7. Test the database connection

```bash
python database/database.py
```

You should see: `Connected to SQL Server successfully!`

### 8. Load starter data (run once)

```bash
python data/sample_data.py
```

This creates 5 branches, 30 customers, their accounts, and 15 loans.

### 9. Start the transaction generator (Terminal 1)

```bash
python transaction_generator.py
```

Leave this running — it will keep creating new transactions every 1–3 seconds. Press `CTRL+C` to stop it.

### 10. Start the dashboard (Terminal 2 — open a new terminal, keep Terminal 1 running)

```bash
streamlit run dashboard/app.py
```

This opens the dashboard in your browser at `http://localhost:8501`, refreshing automatically every few seconds.

## How the Risk Detection Works

Four simple rules are checked on every new transaction:

1. **Large amount** — transaction over ₹100,000 → +40 points
2. **Rapid transactions** — 5+ transactions from the same account within 2 minutes → +25 points
3. **Repeated failures** — 3+ failed transactions from the same account within 10 minutes → +20 points
4. **Deposit-then-withdrawal** — a large withdrawal shortly after a large deposit on the same account → +35 points

Scores combine (capped at 100):
- **0–30** → LOW risk
- **31–70** → MEDIUM risk
- **71–100** → HIGH risk

Flagged transactions are stored in the `suspicious_transactions` table and shown on the dashboard's Risk panel.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Login failed for user` or connection refused | Double-check `DB_SERVER` matches exactly what SSMS uses to connect (including `\SQLEXPRESS` if present) |
| `Data source name not found and no default driver specified` | Your `DB_DRIVER` value in `.env` doesn't match an installed driver — check the exact name in "ODBC Data Sources (64-bit)" → Drivers tab |
| `Cannot open database "banking_analytics"` | Run `schema.sql` in SSMS first (Step 2) |
| `No active accounts found` when generator runs | Run `python data/sample_data.py` first |
| `ModuleNotFoundError` | Make sure your virtual environment is activated and you ran `pip install -r requirements.txt` |
| Dashboard shows no data | Make sure `transaction_generator.py` is running in another terminal |
| `pip install` tries to build pandas/numpy from source (Meson/compiler errors) | Run `python -m pip install --upgrade pip` first, then reinstall. If it still fails, your Python version may be too new for pre-built wheels — installing Python 3.11 or 3.12 usually solves it |

## Disclaimer

This project uses entirely synthetic/simulated data and simplified rule-based logic. It is intended for learning, portfolio, and academic demonstration purposes only, and is not a production banking or fraud-detection system.



