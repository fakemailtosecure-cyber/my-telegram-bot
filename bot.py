import os
import json
import sqlite3
import requests
import time
from threading import Thread
from flask import Flask

# Web Server Render ko active rakhne ke liye
app = Flask('')
@app.route('/')
def home(): return "Full Advanced Bot is Alive!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ================== CONFIGURATION ==================
TOKEN = '8644302388:AAHQ0PsApaZ6Fv11ezOS45uwAHduzERWBrw'
URL = f'https://api.telegram.org/bot{TOKEN}/'
ADMIN_ID = 8644302388  # Aapka Admin Identifier Setup

API_ID = 20408232      
API_HASH = 'b1844f42b78151e7ff3386b32810c18d'
# ===================================================

# DATABASE SETUP
def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY, is_premium INTEGER DEFAULT 0, expiry TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS sessions (chat_id INTEGER, phone TEXT, session_str TEXT)''')
    
    # Saare plans ki default prices aur UPI ID setup
    default_settings = {
        'upi_id': 'sapna512@ptaxis',
        'price_1d': '10',
        'price_3d': '25',
        'price_7d': '50',
        'price_1m': '150',
        'price_perm': '299'
    }
    for key, value in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
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

# BOT FUNCTIONS
def send_message(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup: data['reply_markup'] = json.dumps(reply_markup)
    return requests.post(URL + 'sendMessage', data=data).json()

def edit_message(chat_id, message_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup: data['reply_markup'] = json.dumps(reply_markup)
    requests.post(URL + 'editMessageText', data=data)

# MENUS
def get_main_menu():
    return {"inline_keyboard": [
        [{"text": "➕ Add Session", "callback_data": "add_session"}, {"text": "🚀 Start Mass DM", "callback_data": "start_dm"}],
        [{"text": "📊 Check Progress", "callback_data": "check_progress"}, {"text": "💎 Premium Plans", "callback_data": "premium_plans"}],
        [{"text": "🗑️ Logout Session", "callback_data": "logout_session"}, {"text": "📞 Support", "callback_data": "support"}]
    ]}

def get_premium_menu():
    p1d = get_setting('price_1d')
    p3d = get_setting('price_3d')
    p7d = get_setting('price_7d')
    p1m = get_setting('price_1m')
    pperm = get_setting('price_perm')
    return {"inline_keyboard": [
        [{"text": f"1 Day — ₹{p1d}", "callback_data": "pay_1d"}],
        [{"text": f"3 Days — ₹{p3d}", "callback_data": "pay_3d"}],
        [{"text": f"7 Days — ₹{p7d}", "callback_data": "pay_7d"}],
        [{"text": f"1 Month — ₹{p1m}", "callback_data": "pay_1m"}],
        [{"text": f"Permanent — ₹{pperm}", "callback_data": "pay_perm"}],
        [{"text": "⬅️ Back to Menu", "callback_data": "back_to_menu"}]
    ]}

# POLLING LOOP
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
                        
                        # --- ADMIN COMMANDS ---
                        if text == "/admin":
                            upi = get_setting('upi_id')
                            p1d = get_setting('price_1d')
                            p3d = get_setting('price_3d')
                            p7d = get_setting('price_7d')
                            p1m = get_setting('price_1m')
                            ppm = get_setting('price_perm')
                            
                            admin_text = (
                                f"⚙️ *Admin Control Panel*\n\n"
                                f"**Manual UPI:** `{upi}`\n"
                                f"💰 **Prices:**\n"
                                f"• 1 Day: ₹{p1d} | • 3 Days: ₹{p3d}\n"
                                f"• 7 Days: ₹{p7d} | • 1 Month: ₹{p1m}\n"
                                f"• Permanent: ₹{ppm}\n\n"
                                f"⚙️ **Commands:**\n"
                                f"/setupupi [UPI_ID]\n"
                                f"/setprice1d [Price]\n"
                                f"/setprice3d [Price]\n"
                                f"/setprice7d [Price]\n"
                                f"/setprice1m [Price]\n"
                                f"/setpriceperm [Price]"
                            )
                            send_message(chat_id, admin_text)
                            continue
                            
                        elif text.startswith("/setupupi "):
                            new_upi = text.split(" ", 1)[1]
                            set_setting('upi_id', new_upi)
                            send_message(chat_id, f"✅ UPI ID updated to: `{new_upi}`")
                            continue
                        elif text.startswith("/setprice1d "):
                            set_setting('price_1d', text.split(" ", 1)[1])
                            send_message(chat_id, f"✅ 1 Day price updated!")
                            continue
                        elif text.startswith("/setprice3d "):
                            set_setting('price_3d', text.split(" ", 1)[1])
                            send_message(chat_id, f"✅ 3 Days price updated!")
                            continue
                        elif text.startswith("/setprice7d "):
                            set_setting('price_7d', text.split(" ", 1)[1])
                            send_message(chat_id, f"✅ 7 Days price updated!")
                            continue
                        elif text.startswith("/setprice1m "):
                            set_setting('price_1m', text.split(" ", 1)[1])
                            send_message(chat_id, f"✅ 1 Month price updated!")
                            continue
                        elif text.startswith("/setpriceperm "):
                            set_setting('price_perm', text.split(" ", 1)[1])
                            send_message(chat_id, f"✅ Permanent price updated!")
                            continue
                        
                        # --- USER COMMANDS ---
                        if text == "/start":
                            welcome = "✨ *KUNWAR DMS INCREASER* ✨\n\n*Server Status:* Online 🟢\n\nChoose an option below."
                            send_message(chat_id, welcome, get_main_menu())
                            
                        elif chat_id in user_steps:
                            step = user_steps[chat_id]
                            if step == 'expecting_phone':
                                send_message(chat_id, f"📩 Connecting `{text}`... Sending OTP. Please wait.")
                                send_message(chat_id, "🔑 Enter the OTP received on Telegram:")
                                user_steps[chat_id] = 'expecting_otp'
                            elif step == 'expecting_otp':
                                send_message(chat_id, "✅ Session added successfully (Mock Mode).")
                                del user_steps[chat_id]

                    elif "callback_query" in update:
                        cq = update["callback_query"]
                        chat_id = cq["message"]["chat"]["id"]
                        msg_id = cq["message"]["message_id"]
                        data = cq["data"]
                        
                        if data == "premium_plans":
                            prem_text = "💎 *Premium Plans*\n\nChoose a plan to unlock Mass DM features:"
                            edit_message(chat_id, msg_id, prem_text, get_premium_menu())
                        elif data.startswith("pay_"):
                            plan_type = data.split("_")[1]
                            upi = get_setting('upi_id')
                            price = get_setting(f'price_{plan_type}')
                            
                            pay_text = (
                                f"💳 **Payment Details**\n\n"
                                f"**Plan:** {plan_type.upper()}\n"
                                f"**Amount:** ₹{price}\n"
                                f"**UPI ID:** `{upi}`\n\n"
                                f"👉 Pay on this UPI or use the manual details.\n"
                                f"After payment, send your UTR/Screenshot to Support."
                            )
                            edit_message(chat_id, msg_id, pay_text)
                        elif data == "add_session":
                            send_message(chat_id, "📱 **Add Telegram Session**\n\nPlease send your phone number in international format.\nExample: +919876543210")
                            user_steps[chat_id] = 'expecting_phone'
                        elif data == "back_to_menu":
                            welcome = "✨ *KUNWAR DMS INCREASER* ✨\n\n*Server Status:* Online 🟢"
                            edit_message(chat_id, msg_id, welcome, get_main_menu())
                            
        except Exception as e:
            time.sleep(2)

if __name__ == '__main__':
    Thread(target=run_web_server).start()
    print("Full Advanced Bot Started...")
    bot_polling()
