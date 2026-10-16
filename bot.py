import os
import sqlite3
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "smm_bot.db")
PAYMENT_TEXT = os.getenv(
    "PAYMENT_TEXT",
    "Send payment to your bKash/Nagad/Rocket number, then contact admin with the transaction ID."
)
BRAND = os.getenv("BRAND_NAME", "SMM Services")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS services(
            id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL,
            name TEXT NOT NULL, description TEXT DEFAULT '',
            price_per_1000 REAL NOT NULL, min_qty INTEGER DEFAULT 100,
            max_qty INTEGER DEFAULT 10000, active INTEGER DEFAULT 1
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL, link TEXT NOT NULL, quantity INTEGER NOT NULL,
            total REAL NOT NULL, status TEXT DEFAULT 'Pending',
            created_at TEXT NOT NULL
        )""")
        count = c.execute("SELECT COUNT(*) n FROM services").fetchone()["n"]
        if count == 0:
            c.executemany(
                "INSERT INTO services(category,name,description,price_per_1000,min_qty,max_qty) VALUES(?,?,?,?,?,?)",
                [
                    ("Instagram", "Instagram Followers", "Demo/manual fulfilment service", 120, 100, 10000),
                    ("Instagram", "Instagram Likes", "Demo/manual fulfilment service", 35, 50, 10000),
                    ("YouTube", "YouTube Views", "Demo/manual fulfilment service", 80, 100, 50000),
                    ("TikTok", "TikTok Likes", "Demo/manual fulfilment service", 40, 50, 10000),
                    ("Facebook", "Facebook Page Likes", "Demo/manual fulfilment service", 100, 100, 10000),
                ]
            )

def ensure_user(update: Update):
    u = update.effective_user
    if not u:
        return
    with db() as c:
        c.execute("INSERT OR IGNORE INTO users(user_id, username) VALUES(?,?)", (u.id, u.username or "" ))
        c.execute("UPDATE users SET username=? WHERE user_id=?", (u.username or "", u.id))

def is_admin(uid):
    return ADMIN_ID != 0 and uid == ADMIN_ID

def money(n):
    return f"৳{float(n):.2f}"

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 Browse services", callback_data="categories"),
         InlineKeyboardButton("💰 My balance", callback_data="balance")],
        [InlineKeyboardButton("📦 My orders", callback_data="myorders"),
         InlineKeyboardButton("💳 Add funds info", callback_data="funds")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update)
    context.user_data.clear()
    await update.message.reply_text(
        f"Welcome to *{BRAND}*\\!\\nChoose an option below to browse services and place an order.",
        parse_mode="MarkdownV2", reply_markup=main_menu()
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = ("How to order:\\n1. Browse services.\\n2. Choose a service and enter the target link.\\n"
            "3. Enter quantity.\\n4. Confirm the order.\\n\\nOrders are manually reviewed by the admin. "
            "Only order links/accounts you own or have permission to promote.")
    await update.effective_message.reply_text(text)

async def show_categories(q):
    with db() as c:
        rows = c.execute("SELECT DISTINCT category FROM services WHERE active=1 ORDER BY category").fetchall()
    kb = [[InlineKeyboardButton(r["category"], callback_data="cat:"+r["category"])] for r in rows]
    kb.append([InlineKeyboardButton("⬅️ Main menu", callback_data="home")])
    await q.edit_message_text("Choose a service category:", reply_markup=InlineKeyboardMarkup(kb))

async def show_services(q, category):
    with db() as c:
        rows = c.execute("SELECT * FROM services WHERE active=1 AND category=? ORDER BY id", (category,)).fetchall()
    kb = [[InlineKeyboardButton(f'{r["name"]} — {money(r["price_per_1000"])}/1k', callback_data=f'svc:{r["id"]}')] for r in rows]
    kb.append([InlineKeyboardButton("⬅️ Categories", callback_data="categories")])
    await q.edit_message_text(f"{category} services:", reply_markup=InlineKeyboardMarkup(kb))

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data or ""
    if data == "home":
        await q.edit_message_text(f"{BRAND} — main menu", reply_markup=main_menu())
    elif data == "categories":
        await show_categories(q)
    elif data.startswith("cat:"):
        await show_services(q, data[4:])
    elif data.startswith("svc:"):
        sid = int(data.split(":")[1])
        with db() as c:
            s = c.execute("SELECT * FROM services WHERE id=? AND active=1", (sid,)).fetchone()
        if not s:
            await q.edit_message_text("This service is unavailable.")
            return
        context.user_data.clear()
        context.user_data["order_service_id"] = sid
        context.user_data["step"] = "link"
        await q.edit_message_text(
            f'{s["name"]}\\nPrice: {money(s["price_per_1000"])} per 1,000\\n'
            f'Quantity range: {s["min_qty"]}–{s["max_qty"]}\\n\\nSend the target URL/link now.'
        )
    elif data == "balance":
        with db() as c:
            r = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
        await q.edit_message_text(f"Your balance: {money(r['balance'] if r else 0)}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main menu", callback_data="home")]]))
    elif data == "funds":
        await q.edit_message_text(PAYMENT_TEXT, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main menu", callback_data="home")]]))
    elif data == "myorders":
        with db() as c:
            rows = c.execute("SELECT id,total,status,created_at FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (uid,)).fetchall()
        if not rows:
            text = "You have no orders yet."
        else:
            text = "Your latest orders:\\n" + "\\n".join(f'#{r["id"]} · {r["status"]} · {money(r["total"])} · {r["created_at"]}' for r in rows)
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main menu", callback_data="home")]]))
    elif data == "help":
        await q.edit_message_text("Browse services → choose a service → send target link → enter quantity → confirm. Orders are manually reviewed.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main menu", callback_data="home")]]))
    elif data.startswith("qty:"):
        # Not used; quantity is entered as text.
        pass
    elif data == "confirm_order":
        order = context.user_data.get("pending_order")
        if not order:
            await q.edit_message_text("Order session expired. Start again with /start.")
            return
        with db() as c:
            u = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
            if not u or u["balance"] < order["total"]:
                context.user_data.clear()
                await q.edit_message_text("Insufficient balance. Please add funds and ask admin to credit your balance.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Add funds info", callback_data="funds")]]))
                return
            c.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (order["total"], uid))
            cur = c.execute("INSERT INTO orders(user_id,service_id,link,quantity,total,status,created_at) VALUES(?,?,?,?,?,?,?)",
                            (uid, order["service_id"], order["link"], order["quantity"], order["total"], "Pending", datetime.now().strftime("%Y-%m-%d %H:%M")))
            oid = cur.lastrowid
            s = c.execute("SELECT name FROM services WHERE id=?", (order["service_id"],)).fetchone()
        context.user_data.clear()
        await q.edit_message_text(f"✅ Order placed!\\nOrder ID: #{oid}\\nService: {s['name']}\\nTotal: {money(order['total'])}\\nStatus: Pending")
        if ADMIN_ID:
            try:
                await context.bot.send_message(ADMIN_ID, f"📦 New order #{oid}\\nUser: {uid} (@{q.from_user.username or 'no_username'})\\nService: {s['name']}\\nLink: {order['link']}\\nQuantity: {order['quantity']}\\nTotal: {money(order['total'])}\\nStatus: Pending\\nUse /orders to manage.")
            except Exception:
                log.exception("Could not notify admin")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update)
    step = context.user_data.get("step")
    if step == "link":
        link = (update.message.text or "").strip()
        if len(link) < 5 or " " in link:
            await update.message.reply_text("Please send a valid URL/link (no spaces).")
            return
        context.user_data["order_link"] = link
        context.user_data["step"] = "quantity"
        sid = context.user_data["order_service_id"]
        with db() as c:
            s = c.execute("SELECT min_qty,max_qty FROM services WHERE id=?", (sid,)).fetchone()
        await update.message.reply_text(f"Enter quantity ({s['min_qty']}–{s['max_qty']}):")
    elif step == "quantity":
        try:
            qty = int((update.message.text or "").strip())
        except ValueError:
            await update.message.reply_text("Enter quantity as a whole number.")
            return
        sid = context.user_data["order_service_id"]
        with db() as c:
            s = c.execute("SELECT * FROM services WHERE id=? AND active=1", (sid,)).fetchone()
        if not s or qty < s["min_qty"] or qty > s["max_qty"]:
            await update.message.reply_text(f"Quantity must be between {s['min_qty']} and {s['max_qty']}.")
            return
        total = round((qty / 1000) * s["price_per_1000"], 2)
        order = {"service_id": sid, "link": context.user_data["order_link"], "quantity": qty, "total": total}
        context.user_data["pending_order"] = order
        context.user_data.pop("step", None)
        await update.message.reply_text(
            f"Confirm order?\\nService: {s['name']}\\nLink: {order['link']}\\nQuantity: {qty}\\nTotal: {money(total)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm", callback_data="confirm_order"),
                                                InlineKeyboardButton("❌ Cancel", callback_data="home")]])
        )
    elif is_admin(update.effective_user.id):
        await admin_text(update, context)
    else:
        await update.message.reply_text("Use /start to open the menu.")

async def admin_text(update, context):
    # Admin free-text commands are handled via commands; keep this safe fallback.
    await update.message.reply_text("Admin commands: /admin, /addservice, /services, /orders, /setstatus, /credit, /debit, /users")

def admin_only(fn):
    async def wrapper(update, context):
        if not is_admin(update.effective_user.id):
            await update.effective_message.reply_text("Admin only.")
            return
        return await fn(update, context)
    return wrapper

@admin_only
async def admin_cmd(update, context):
    await update.message.reply_text(
        "Admin commands:\\n"
        "/addservice CATEGORY | NAME | PRICE_PER_1000 | MIN | MAX | DESCRIPTION\\n"
        "/services — list services\\n"
        "/off SERVICE_ID / /on SERVICE_ID\\n"
        "/orders — latest orders\\n"
        "/setstatus ORDER_ID STATUS\\n"
        "/credit USER_ID AMOUNT\\n/debit USER_ID AMOUNT\\n"
        "/users — recent users\\n"
        "Statuses: Pending, In Progress, Completed, Cancelled"
    )

@admin_only
async def addservice_cmd(update, context):
    raw = update.message.text.partition(" ")[2]
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 5:
        await update.message.reply_text("Usage: /addservice CATEGORY | NAME | PRICE_PER_1000 | MIN | MAX | DESCRIPTION")
        return
    try:
        category, name = parts[0], parts[1]
        price, minq, maxq = float(parts[2]), int(parts[3]), int(parts[4])
        desc = parts[5] if len(parts) > 5 else ""
        if price < 0 or minq < 1 or maxq < minq: raise ValueError()
    except ValueError:
        await update.message.reply_text("Invalid price or quantity range.")
        return
    with db() as c:
        cur = c.execute("INSERT INTO services(category,name,description,price_per_1000,min_qty,max_qty) VALUES(?,?,?,?,?,?)", (category,name,desc,price,minq,maxq))
    await update.message.reply_text(f"Added service ID {cur.lastrowid}: {name}")

@admin_only
async def services_cmd(update, context):
    with db() as c:
        rows = c.execute("SELECT * FROM services ORDER BY id").fetchall()
    if not rows:
        await update.message.reply_text("No services.")
        return
    await update.message.reply_text("\\n".join(f'#{r["id"]} [{ "ON" if r["active"] else "OFF" }] {r["category"]} — {r["name"]} — {money(r["price_per_1000"])}/1k (min {r["min_qty"]}, max {r["max_qty"]})' for r in rows))

@admin_only
async def toggle_service(update, context, active):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /on SERVICE_ID or /off SERVICE_ID")
        return
    sid = int(context.args[0])
    with db() as c:
        c.execute("UPDATE services SET active=? WHERE id=?", (active,sid))
    await update.message.reply_text("Updated service.")

@admin_only
async def on_cmd(update, context): await toggle_service(update, context, 1)
@admin_only
async def off_cmd(update, context): await toggle_service(update, context, 0)

@admin_only
async def orders_cmd(update, context):
    with db() as c:
        rows = c.execute("""SELECT o.*,u.username FROM orders o LEFT JOIN users u ON u.user_id=o.user_id ORDER BY o.id DESC LIMIT 20""").fetchall()
    if not rows:
        await update.message.reply_text("No orders.")
        return
    await update.message.reply_text("\\n".join(f'#{r["id"]} | {r["status"]} | user {r["user_id"]} (@{r["username"] or "?"}) | service {r["service_id"]} | qty {r["quantity"]} | {money(r["total"])}' for r in rows))

@admin_only
async def setstatus_cmd(update, context):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /setstatus ORDER_ID STATUS")
        return
    try: oid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Order ID must be a number."); return
    status = " ".join(context.args[1:]).replace("_", " ").title()
    allowed = {"Pending","In Progress","Completed","Cancelled"}
    if status not in allowed:
        await update.message.reply_text("Status must be: Pending, In_Progress, Completed, or Cancelled.")
        return
    with db() as c:
        order = c.execute("SELECT user_id,total,status FROM orders WHERE id=?", (oid,)).fetchone()
        if not order:
            await update.message.reply_text("Order not found."); return
        c.execute("UPDATE orders SET status=? WHERE id=?", (status,oid))
        if status == "Cancelled" and order["status"] != "Cancelled":
            c.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (order["total"],order["user_id"]))
    await update.message.reply_text(f"Order #{oid} status updated to {status}. If cancelled, the balance was refunded.")
    try:
        await context.bot.send_message(order["user_id"], f"Update: Order #{oid} status is now {status}." + (" Your balance was refunded." if status == "Cancelled" else ""))
    except Exception: pass

@admin_only
async def balance_change(update, context, sign):
    if len(context.args) != 2:
        await update.message.reply_text(f"Usage: /{'credit' if sign == 1 else 'debit'} USER_ID AMOUNT"); return
    try:
        uid, amount = int(context.args[0]), float(context.args[1])
        if amount <= 0: raise ValueError()
    except ValueError:
        await update.message.reply_text("Enter a valid user ID and positive amount."); return
    with db() as c:
        u = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
        if not u:
            await update.message.reply_text("User not found. They must start the bot first."); return
        if sign == -1 and u["balance"] < amount:
            await update.message.reply_text("User has insufficient balance."); return
        c.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (sign*amount,uid))
        newbal = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()["balance"]
    await update.message.reply_text(f"Updated. New balance: {money(newbal)}")
    try: await context.bot.send_message(uid, f"Your balance was {'credited' if sign==1 else 'debited'} by {money(amount)}. New balance: {money(newbal)}")
    except Exception: pass

@admin_only
async def credit_cmd(update, context): await balance_change(update, context, 1)
@admin_only
async def debit_cmd(update, context): await balance_change(update, context, -1)

@admin_only
async def users_cmd(update, context):
    with db() as c:
        rows = c.execute("SELECT user_id,username,balance FROM users ORDER BY rowid DESC LIMIT 30").fetchall()
    await update.message.reply_text("Recent users:\\n" + ("\\n".join(f'{r["user_id"]} @{r["username"] or "?"} balance {money(r["balance"])}' for r in rows) if rows else "No users."))

def main():
    if not TOKEN:
        raise SystemExit("Set BOT_TOKEN environment variable first.")
    if ADMIN_ID == 0:
        raise SystemExit("Set ADMIN_ID environment variable to your Telegram numeric user ID.")
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("addservice", addservice_cmd))
    app.add_handler(CommandHandler("services", services_cmd))
    app.add_handler(CommandHandler("on", on_cmd))
    app.add_handler(CommandHandler("off", off_cmd))
    app.add_handler(CommandHandler("orders", orders_cmd))
    app.add_handler(CommandHandler("setstatus", setstatus_cmd))
    app.add_handler(CommandHandler("credit", credit_cmd))
    app.add_handler(CommandHandler("debit", debit_cmd))
    app.add_handler(CommandHandler("users", users_cmd))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    log.info("Bot is running")
    app.run_polling()

if __name__ == "__main__":
    main()
