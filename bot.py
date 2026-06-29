import os
import json
import sqlite3
import requests
import time
from threading import Thread
from flask import Flask

# Web Server Render ke liye
app = Flask('')
@app.route('/')
def home(): return "Advanced Bot is Alive!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ================== CONFIGURATION ==================
TOKEN = '8644302388:AAHQ0PsApaZ6Fv11ezOS45uwAHduzERWBrw'
URL = f'https://api.telegram.org/bot{TOKEN}/'
ADMIN_ID = 8644302388  # <--- Aapka Bot Admin Identifier Setup

# Standard API Details generic usage ke liye
API_ID = 20408232      
API_HASH = 'b1844f42b78151e7ff3386b32810c18d'
# ===================================================

# DATABASE SETUP (Data yaad rakhne ke liye)
def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY, is_premium INTEGER DEFAULT 0, expiry TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS sessions (chat_id INTEGER, phone TEXT, session_str TEXT)''')
    
    # Default parameters agar table khali hai
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('upi_id', 'sapna512@ptaxis')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('price_1d', '10')")
    conn.commit()
    conn.close()

init_db()

def get_setting(key):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else "Not Set"

def set_setting(key, value):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# TELEGRAM BOT HELPER METHODS
def send_message(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup: data['reply_markup'] = json.dumps(reply_markup)
    return requests.post(URL + 'sendMessage', data=data).json()

def edit_message(chat_id, message_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup: data['reply_markup'] = json.dumps(reply_markup)
    requests.post(URL + 'editMessageText', data=data)

# INTERFACE MENUS
def get_main_menu():
    return {"inline_keyboard": [
        [{"text": "➕ Add Session", "callback_data": "add_session"}, {"text": "🚀 Start Mass DM", "callback_data": "start_dm"}],
        [{"text": "📊 Check Progress", "callback_data": "check_progress"}, {"text": "💎 Premium Plans", "callback_data": "premium_plans"}],
        [{"text": "🗑️ Logout Session", "callback_data": "logout_session"}, {"text": "📞 Support", "callback_data": "support"}]
    ]}

def get_premium_menu():
    p_1d = get_setting('price_1d')
    return {"inline_keyboard": [
        [{"text": f"1 Day — ₹{p_1d}", "callback_data": "pay_1d"}],
        [{"text": "⬅️ Back to Menu", "callback_data": "back_to_menu"}]
    ]}

# BOT LISTENER FUNCTION
def bot_polling():
    offset = 0
    user_steps = {}
    
    while True:
        try:
            r = requests.get(URL + 'getUpdates', params={'offset': offset, 'timeout': 1}).json()
            if "result" in r:
                for update in r["result"]:
                    offset = update["update_id"] + 1
                    
                    if "message" in update and "text" in update["message"]:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        text = msg["text"]
                        
                        # --- ADMIN EXCLUSIVE CONTROLS ---
                        if text == "/admin":
                            upi = get_setting('upi_id')
                            p1d = get_setting('price_1d')
                            admin_text = f"⚙️ **Admin Control Panel**\n\n**Manual UPI:** `{upi}`\n**1 Day Price:** ₹{p1d}\n\n**Setup Commands:**\n/setupupi [UPI_ID]\n/setprice1d [INR]"
                            send_message(chat_id, admin_text)
                            continue
                        elif text.startswith("/setupupi "):
                            new_upi = text.split(" ", 1)[1]
                            set_setting('upi_id', new_upi)
                            send_message(chat_id, f"✅ UPI ID updated to: `{new_upi}`")
                            continue
                        elif text.startswith("/setprice1d "):
                            new_price = text.split(" ", 1)[1]
                            set_setting('price_1d', new_price)
                            send_message(chat_id, f"✅ 1 Day Price set to: ₹{new_price}")
                            continue
                        
                        # --- SYSTEM COMMANDS ---
                        if text == "/start":
                            welcome = "✨ *KUNWAR DMS INCREASER* ✨\n\n*Server Status:* Online 🟢\n*Database:* Connected 💾\n\nChoose an option below."
                            send_message(chat_id, welcome, get_main_menu())
                            
                        elif chat_id in user_steps:
                            step = user_steps[chat_id]
                            if step == 'expecting_phone':
                                send_message(chat_id, f"📩 Connecting `{text}`... Requesting secure login.")
                                send_message(chat_id, "🔑 Enter the temporary code sent to your device:")
                                user_steps[chat_id] = 'expecting_otp'
                            elif step == 'expecting_otp':
                                send_message(chat_id, "✅ Connection updated and registered.")
                                del user_steps[chat_id]

                    elif "callback_query" in update:
                        cq = update["callback_query"]
                        chat_id = cq["message"]["chat"]["id"]
                        msg_id = cq["message"]["message_id"]
                        data = cq["data"]
                        
                        if data == "premium_plans":
                            p1d = get_setting('price_1d')
                            prem_text = f"💎 *Premium Plans*\n\nSelect a subscription model:\n\n1️⃣ 1 Day — ₹{p1d}"
                            edit_message(chat_id, msg_id, prem_text, get_premium_menu())
                        elif data == "pay_1d":
                            upi = get_setting('upi_id')
                            p1d = get_setting('price_1d')
                            pay_text = f"💳 **Payment Details**\n\n**Plan:** 1 Day\n**Amount:** ₹{p1d}\n**UPI ID:** `{upi}`\n\n👉 Pay via your preferred UPI gateway.\nOnce completed, forward the verification details."
                            edit_message(chat_id, msg_id, pay_text)
                        elif data == "add_session":
                            send_message(chat_id, "📱 **Add Telegram Session**\n\nPlease submit your phone number in international format.\nExample: +919876543210")
                            user_steps[chat_id] = 'expecting_phone'
                        elif data == "back_to_menu":
                            welcome = "✨ *KUNWAR DMS INCREASER* ✨\n\n*Server Status:* Online 🟢"
                            edit_message(chat_id, msg_id, welcome, get_main_menu())
                            
        except Exception as e:
            time.sleep(2)

if __name__ == '__main__':
    Thread(target=run_web_server).start()
    print("Advanced Core is starting...")
    bot_polling()
