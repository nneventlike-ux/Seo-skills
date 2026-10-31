"""A small, payment-free Telegram shopping demo."""

import json
import os
import sqlite3
import stat
import time
import urllib.error
import urllib.request

PRODUCTS = {
    "1": ("Studio Headphones", 12900),
    "2": ("Everyday Backpack", 7900),
    "3": ("Minimal Watch", 14900),
    "4": ("Portable Speaker", 5900),
    "5": ("Classic Sunglasses", 4900),
}


def connect(path):
    if path != ":memory:":
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                raise PermissionError("Bot database must be a private regular file (mode 0600).")
        finally:
            os.close(descriptor)
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY, update_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL, product_name TEXT NOT NULL,
            price_cents INTEGER NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value INTEGER NOT NULL);
    """)
    return db


def catalog():
    lines = [f"{key}. {name} — ${cents / 100:.2f}" for key, (name, cents) in PRODUCTS.items()]
    return "Demo catalog:\n" + "\n".join(lines) + "\n\nUse /order <number> to place a demo order."


def reply(db, message, update_id):
    chat = message.get("chat", {})
    if chat.get("type") != "private" or not isinstance(chat.get("id"), int):
        return None
    chat_id = chat["id"]
    parts = message.get("text", "").split()
    command = parts[0].split("@")[0].lower() if parts else ""
    if command in ("/start", "/help"):
        return chat_id, "Demo shop: /catalog, /order <number>, /orders. No payment or delivery is provided."
    if command == "/catalog":
        return chat_id, catalog()
    if command == "/order":
        product = PRODUCTS.get(parts[1]) if len(parts) == 2 else None
        if not product:
            return chat_id, "Choose a product with /order <number>. Use /catalog to see the list."
        name, cents = product
        db.execute("INSERT INTO orders (update_id, chat_id, product_name, price_cents) VALUES (?, ?, ?, ?)", (update_id, chat_id, name, cents))
        return chat_id, f"Demo order placed: {name} (${cents / 100:.2f}). No payment was taken."
    if command == "/orders":
        rows = db.execute("SELECT id, product_name, price_cents FROM orders WHERE chat_id = ? ORDER BY id DESC LIMIT 10", (chat_id,)).fetchall()
        lines = [f"#{order_id}: {name} — ${cents / 100:.2f}" for order_id, name, cents in rows]
        return chat_id, "Demo orders:\n" + "\n".join(lines) if lines else "You have no demo orders."
    return chat_id, "Use /help to see the available commands."


def process_update(db, update):
    update_id = update["update_id"]
    with db:
        row = db.execute("SELECT value FROM state WHERE key = 'offset'").fetchone()
        if row and update_id < row[0]:
            return None
        response = reply(db, update.get("message", {}), update_id)
        db.execute("INSERT INTO state (key, value) VALUES ('offset', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (update_id + 1,))
        db.execute("INSERT INTO state (key, value) VALUES ('last_update', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (int(time.time()),))
    return response


def telegram(token, method, payload):
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise ValueError("Telegram rejected the request")
    return result["result"]


def polling_offset(db):
    with db:
        last = db.execute("SELECT value FROM state WHERE key = 'last_update'").fetchone()
        if last and time.time() - last[0] >= 6 * 24 * 60 * 60:
            db.execute("DELETE FROM state WHERE key IN ('offset', 'last_update')")
        row = db.execute("SELECT value FROM state WHERE key = 'offset'").fetchone()
    return row[0] if row else 0


def run(db, token):
    while True:
        try:
            updates = telegram(token, "getUpdates", {"offset": polling_offset(db), "timeout": 30, "allowed_updates": ["message"]})
            for update in updates:
                response = process_update(db, update)
                if response:
                    chat_id, text = response
                    telegram(token, "sendMessage", {"chat_id": chat_id, "text": text})
        except (urllib.error.URLError, TimeoutError, ValueError, OSError):
            print("Telegram request failed; retrying in 5 seconds.", flush=True)
            time.sleep(5)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN before starting the bot.")
    path = os.environ.get("BOT_DATABASE_PATH", "bot-demo.sqlite3")
    with connect(path) as db:
        run(db, token)


if __name__ == "__main__":
    main()
