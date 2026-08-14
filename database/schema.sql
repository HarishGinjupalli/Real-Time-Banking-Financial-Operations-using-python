-- =========================================================
-- Real-Time Banking Financial Operations & Transaction
-- Analytics System - Database Schema (Microsoft SQL Server)
-- =========================================================
-- Run this file in SQL Server Management Studio (SSMS):
--   1. Open SSMS and connect to your local server
--      (e.g. localhost or localhost\SQLEXPRESS)
--   2. Click "New Query"
--   3. Paste this entire file in and click "Execute" (or F5)
-- =========================================================

-- Create the database (only if it does not already exist)
IF DB_ID('banking_analytics') IS NULL
BEGIN
    CREATE DATABASE banking_analytics;
END
GO

USE banking_analytics;
GO

-- ---------------------------------------------------------
-- Table: branches
-- Stores information about each bank branch.
-- ---------------------------------------------------------
IF OBJECT_ID('dbo.branches', 'U') IS NULL
BEGIN
    CREATE TABLE branches (
        branch_id INT IDENTITY(1,1) PRIMARY KEY,
        branch_name VARCHAR(100) NOT NULL,
        city VARCHAR(50) NOT NULL,
        state VARCHAR(50) NOT NULL
    );
END
GO

-- ---------------------------------------------------------
-- Table: customers
-- Stores basic details about each bank customer.
-- ---------------------------------------------------------
IF OBJECT_ID('dbo.customers', 'U') IS NULL
BEGIN
    CREATE TABLE customers (
        customer_id INT IDENTITY(1,1) PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        age INT NOT NULL,
        gender VARCHAR(10) NOT NULL,
        city VARCHAR(50) NOT NULL,
        state VARCHAR(50) NOT NULL,
        customer_type VARCHAR(20) NOT NULL,        -- e.g. INDIVIDUAL, BUSINESS
        account_open_date DATE NOT NULL
    );
END
GO

-- ---------------------------------------------------------
-- Table: accounts
-- Each customer can have one or more bank accounts.
-- Every account belongs to one branch.
-- ---------------------------------------------------------
IF OBJECT_ID('dbo.accounts', 'U') IS NULL
BEGIN
    CREATE TABLE accounts (
        account_id INT IDENTITY(1,1) PRIMARY KEY,
        customer_id INT NOT NULL,
        branch_id INT NOT NULL,
        account_type VARCHAR(20) NOT NULL,          -- e.g. SAVINGS, CURRENT
        balance DECIMAL(15,2) NOT NULL DEFAULT 0,
        account_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE, CLOSED
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_accounts_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
        CONSTRAINT FK_accounts_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
    );
END
GO

-- ---------------------------------------------------------
-- Table: transactions
-- Every banking transaction (deposit, withdrawal, transfer,
-- UPI, ATM, card, loan payment, fee) is stored here.
-- source_account / destination_account are only used for
-- TRANSFER transactions (money moving between two accounts).
-- ---------------------------------------------------------
IF OBJECT_ID('dbo.transactions', 'U') IS NULL
BEGIN
    CREATE TABLE transactions (
        transaction_id INT IDENTITY(1,1) PRIMARY KEY,
        account_id INT NOT NULL,
        transaction_type VARCHAR(20) NOT NULL,       -- DEPOSIT, WITHDRAWAL, TRANSFER, ATM, UPI, CARD, LOAN_PAYMENT, FEE
        transaction_amount DECIMAL(15,2) NOT NULL,
        transaction_channel VARCHAR(30) NOT NULL,    -- ATM, UPI, MOBILE_BANKING, INTERNET_BANKING, BRANCH, DEBIT_CARD, CREDIT_CARD
        transaction_status VARCHAR(20) NOT NULL,     -- SUCCESS, FAILED, PENDING
        transaction_timestamp DATETIME NOT NULL DEFAULT GETDATE(),
        source_account INT NULL,
        destination_account INT NULL,
        branch_id INT NOT NULL,
        CONSTRAINT FK_transactions_account FOREIGN KEY (account_id) REFERENCES accounts(account_id),
        CONSTRAINT FK_transactions_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
    );
END
GO

-- ---------------------------------------------------------
-- Table: loans
-- Stores loans taken by customers.
-- ---------------------------------------------------------
IF OBJECT_ID('dbo.loans', 'U') IS NULL
BEGIN
    CREATE TABLE loans (
        loan_id INT IDENTITY(1,1) PRIMARY KEY,
        customer_id INT NOT NULL,
        loan_type VARCHAR(30) NOT NULL,          -- HOME, CAR, PERSONAL, EDUCATION
        loan_amount DECIMAL(15,2) NOT NULL,
        interest_rate DECIMAL(5,2) NOT NULL,
        outstanding_amount DECIMAL(15,2) NOT NULL,
        loan_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE, CLOSED
        start_date DATE NOT NULL,
        CONSTRAINT FK_loans_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );
END
GO

-- ---------------------------------------------------------
-- Table: loan_payments
-- Stores each repayment made against a loan.
-- ---------------------------------------------------------
IF OBJECT_ID('dbo.loan_payments', 'U') IS NULL
BEGIN
    CREATE TABLE loan_payments (
        payment_id INT IDENTITY(1,1) PRIMARY KEY,
        loan_id INT NOT NULL,
        payment_amount DECIMAL(15,2) NOT NULL,
        payment_date DATE NOT NULL,
        payment_status VARCHAR(20) NOT NULL,     -- SUCCESS, FAILED
        CONSTRAINT FK_loanpayments_loan FOREIGN KEY (loan_id) REFERENCES loans(loan_id)
    );
END
GO

-- ---------------------------------------------------------
-- Table: suspicious_transactions
-- Stores transactions flagged by our simple rule-based
-- risk system, along with a risk score and risk level.
-- ---------------------------------------------------------
IF OBJECT_ID('dbo.suspicious_transactions', 'U') IS NULL
BEGIN
    CREATE TABLE suspicious_transactions (
        alert_id INT IDENTITY(1,1) PRIMARY KEY,
        transaction_id INT NOT NULL,
        alert_type VARCHAR(200) NOT NULL,        -- which rule(s) triggered the alert
        risk_score INT NOT NULL,                 -- 0 to 100
        risk_level VARCHAR(20) NOT NULL,         -- LOW, MEDIUM, HIGH
        alert_status VARCHAR(20) NOT NULL DEFAULT 'OPEN',  -- OPEN, REVIEWED
        created_at DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_suspicious_transaction FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id)
    );
END
GO
