from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import sqlite3
from fpdf import FPDF
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'secretkey'
DB_NAME = "bank.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        account_no TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        pin TEXT NOT NULL,
                        balance REAL DEFAULT 0.0
                     )''')
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_no TEXT,
                        type TEXT,
                        amount REAL,
                        timestamp TEXT
                     )''')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    account_no = request.form['account_no']
    pin = request.form['pin']
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (account_no, name, pin) VALUES (?, ?, ?)", (account_no, name, pin))
            conn.commit()
            flash("Account created successfully!", "success")
        except:
            flash("Account already exists.", "danger")
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    account_no = request.form['account_no']
    pin = request.form['pin']
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE account_no=? AND pin=?", (account_no, pin))
        user = c.fetchone()
    if user:
        session['account_no'] = account_no
        session['name'] = user[1]
        return redirect(url_for('dashboard'))
    flash("Invalid account number or PIN.", "danger")
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'account_no' not in session:
        return redirect(url_for('index'))
    account_no = session['account_no']
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT balance FROM users WHERE account_no=?", (account_no,))
        balance = c.fetchone()[0]
        c.execute("SELECT type, amount, timestamp FROM transactions WHERE account_no=? ORDER BY timestamp DESC", (account_no,))
        transactions = c.fetchall()
    return render_template('dashboard.html', name=session['name'], balance=balance, transactions=transactions)

@app.route('/transaction', methods=['POST'])
def transaction():
    if 'account_no' not in session:
        return redirect(url_for('index'))
    account_no = session['account_no']
    ttype = request.form['type']
    amount = float(request.form['amount'])
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        if ttype == 'Deposit':
            c.execute("UPDATE users SET balance = balance + ? WHERE account_no=?", (amount, account_no))
            flash("Deposit successful!", "success")
        elif ttype == 'Withdraw':
            c.execute("SELECT balance FROM users WHERE account_no=?", (account_no,))
            balance = c.fetchone()[0]
            if amount > balance:
                flash("Insufficient balance for withdrawal.", "danger")
                return redirect(url_for('dashboard'))
            c.execute("UPDATE users SET balance = balance - ? WHERE account_no=?", (amount, account_no))
            flash("Withdrawal successful!", "success")
        c.execute("INSERT INTO transactions (account_no, type, amount, timestamp) VALUES (?, ?, ?, ?)",
                  (account_no, ttype, amount, datetime.now().isoformat()))
        conn.commit()
    return redirect(url_for('dashboard'))

@app.route('/download_pdf')
def download_pdf():
    account_no = session.get('account_no')
    if not account_no:
        return redirect(url_for('index'))
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT type, amount, timestamp FROM transactions WHERE account_no=? ORDER BY timestamp DESC", (account_no,))
        transactions = c.fetchall()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Transaction Report", ln=1, align="C")
    for t in transactions:
        pdf.cell(200, 10, txt=f"{t[2]} | {t[0]} | Rs.{t[1]}", ln=1)
    filepath = "transaction_report.pdf"
    pdf.output(filepath)
    return send_file(filepath, as_attachment=True)

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
