import sqlite3, hashlib, os, json, io
import pandas as pd

DB_PATH = os.environ.get("RUANGUANG_DB", "ruanguang.db")

def conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            kind TEXT NOT NULL,
            opening_balance REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT,
            account TEXT NOT NULL,
            tx_date TEXT NOT NULL,
            note TEXT,
            transfer_peer TEXT
        );
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            provider TEXT,
            amount REAL NOT NULL,
            due_date TEXT NOT NULL,
            note TEXT,
            paid INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
        """)

def add_account(name, kind, opening):
    with conn() as c:
        c.execute("INSERT INTO accounts(name,kind,opening_balance) VALUES(?,?,?)", (name,kind,opening))

def get_accounts():
    with conn() as c:
        rows = c.execute("SELECT * FROM accounts ORDER BY id").fetchall()
        result = []
        for r in rows:
            income = c.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE account=? AND kind IN ('Income','Transfer In')", (r["name"],)).fetchone()[0]
            expense = c.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE account=? AND kind IN ('Expense','Transfer Out')", (r["name"],)).fetchone()[0]
            result.append({"id":r["id"],"name":r["name"],"kind":r["kind"],"balance":r["opening_balance"]+income-expense})
        return result

def delete_account(account_id):
    with conn() as c:
        row = c.execute("SELECT name FROM accounts WHERE id=?", (account_id,)).fetchone()
        if row:
            # Keep historical transactions; only remove the account from the active account list.
            c.execute("DELETE FROM accounts WHERE id=?", (account_id,))

def add_transaction(kind, amount, category, account, tx_date, note="", transfer_peer=None):
    with conn() as c:
        c.execute("""INSERT INTO transactions(kind,amount,category,account,tx_date,note,transfer_peer)
        VALUES(?,?,?,?,?,?,?)""", (kind,float(amount),category,account,tx_date,note,transfer_peer))

def get_transactions(limit=1000):
    with conn() as c:
        return pd.read_sql_query("SELECT * FROM transactions ORDER BY tx_date DESC, id DESC LIMIT ?", c, params=(limit,))

def delete_transaction(tx_id):
    with conn() as c:
        c.execute("DELETE FROM transactions WHERE id=?", (tx_id,))

def get_total_balance():
    return sum(a["balance"] for a in get_accounts())

def add_bill(title, provider, amount, due_date, note):
    with conn() as c:
        c.execute("INSERT INTO bills(title,provider,amount,due_date,note) VALUES(?,?,?,?,?)", (title,provider,amount,due_date,note))

def get_bills():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM bills ORDER BY paid ASC, due_date ASC").fetchall()]

def update_bill(bill_id, paid):
    with conn() as c:
        c.execute("UPDATE bills SET paid=? WHERE id=?", (int(paid),bill_id))

def delete_bill(bill_id):
    with conn() as c:
        c.execute("DELETE FROM bills WHERE id=?", (bill_id,))

def set_pin(pin):
    digest = hashlib.sha256(pin.encode("utf-8")).hexdigest()
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('pin_hash',?)", (digest,))

def get_pin_hash():
    with conn() as c:
        row = c.execute("SELECT value FROM settings WHERE key='pin_hash'").fetchone()
        return row["value"] if row else None

def verify_pin(pin, digest):
    return hashlib.sha256(pin.encode("utf-8")).hexdigest() == digest

def clear_pin():
    with conn() as c:
        c.execute("DELETE FROM settings WHERE key='pin_hash'")

def export_all():
    with conn() as c:
        data = {
            "accounts":[dict(r) for r in c.execute("SELECT * FROM accounts").fetchall()],
            "transactions":[dict(r) for r in c.execute("SELECT * FROM transactions").fetchall()],
            "bills":[dict(r) for r in c.execute("SELECT * FROM bills").fetchall()]
        }
    return json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")

def import_transactions(uploaded_file):
    df = pd.read_csv(uploaded_file)
    required = {"kind","amount","category","account","tx_date"}
    if not required.issubset(df.columns):
        raise ValueError("Kolom wajib: kind, amount, category, account, tx_date")
    count = 0
    for _, r in df.iterrows():
        add_transaction(str(r["kind"]), float(r["amount"]), str(r["category"]), str(r["account"]), str(r["tx_date"]), str(r.get("note","")))
        count += 1
    return count

def delete_all_transactions():
    with conn() as c:
        c.execute("DELETE FROM transactions")
