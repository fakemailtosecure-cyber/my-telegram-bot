import os
import json
import sqlite3
import requests
import time
from threading import Thread
from flask import Flask

app = Flask('')
@app.route('/')
def home(): return "Kunwar DMS Mega Bot is Alive!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ================== CONFIGURATION ==================
TOKEN = '8644302388:AAHQ0PsApaZ6Fv11ezOS45uwAHduzERWBrw'
URL = f'https://api.telegram.org/bot{TOKEN}/'
ADMIN_ID = 8644302388  

# 🔗 [YAHAN APNE LOGO BANNER KA URL DALO]
# Agar aapke paas direct link nahi hai, toh abhi is link ko chalne dein
START_IMAGE_URL = 'https://telegra.ph/file/0c968f94d3a82efda1608.jpg' 
# ===================================================

# DATABASE SETUP
def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY, is_premium INTEGER DEFAULT 0, expiry TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    
    default_settings = {
        'upi_id': 'sapna513@ptaxis',
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

# TELEGRAM GRAPHICS HELPERS
def send_photo(chat_id, photo_url, caption, reply_markup=None):
    data = {'chat_id': chat_id, 'photo': photo_url, 'caption': caption, 'parse_mode': 'Markdown'}
    if reply_markup: data['reply_markup'] = json.dumps(reply_markup)
    return requests.post(URL + 'sendPhoto', data=data).json()

def send_message(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup: data['reply_markup'] = json.dumps(reply_markup)
    return requests.post(URL + 'sendMessage', data=data).json()

def edit_message(chat_id, message_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup: data['reply_markup'] = json.dumps(reply_markup)
    requests.post(URL + 'editMessageText', data=data)

# KEYBOARDS SETUP
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

def get_payment_action_buttons():
    return {"inline_keyboard": [
        [{"text": "PAID ✅", "callback_data": "payment_paid"}, {"text": "CANCEL ❌", "callback_data": "back_to_menu"}]
    ]}

# POLLING PROCESSING
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
                        
                        # --- ADMIN CONTROLS ---
                        if text == "/admin" and chat_id == ADMIN_ID:
                            upi = get_setting('upi_id')
                            admin_text = (
                                f"⚙️ *Admin Control Panel*\n\n"
                                f"**Manual UPI:** `{upi}`\n\n"
                                f"💡 *Prices Setup Commands:*\n"
                                f"/setupupi [UPI_ID]\n"
                                f"/setprice1d [Price] | /setprice3d [Price]\n"
                                f"/setprice7d [Price] | /setprice1m [Price]\n"
                                f"/setpriceperm [Price]"
                            )
                            send_message(chat_id, admin_text)
                            continue
                            
                        elif text.startswith("/setupupi ") and chat_id == ADMIN_ID:
                            new_upi = text.split(" ", 1)[1]
                            set_setting('upi_id', new_upi)
                            send_message(chat_id, f"✅ UPI ID updated to: `{new_upi}`")
                            continue
                        elif text.startswith("/setprice") and chat_id == ADMIN_ID:
                            cmd_parts = text.split(" ")
                            plan_key = cmd_parts[0].replace("/setprice", "price_")
                            set_setting(plan_key, cmd_parts[1])
                            send_message(chat_id, f"✅ {plan_key.upper()} set to ₹{cmd_parts[1]}")
                            continue
                        
                        # --- USER CONTROLS ---
                        if text == "/start":
                            welcome = "✨ *KUNWAR DMS INCREASER* ✨\n\n*Server Status:* Online 🟢\n*System:* Active\n*Security:* Enabled\n\nChoose an option below."
                            # Direct Image mapping for start banner
                            send_photo(chat_id, START_IMAGE_URL, welcome, get_main_menu())
                            continue
                            
                        elif chat_id in user_steps:
                            if user_steps[chat_id] == 'expecting_phone':
                                send_message(chat_id, "📩 Connecting... Requesting login code.")
                                del user_steps[chat_id]

                    elif "callback_query" in update:
                        cq = update["callback_query"]
                        chat_id = cq["message"]["chat"]["id"]
                        msg_id = cq["message"]["message_id"]
                        data = cq["data"]
                        
                        if data == "premium_plans":
                            prem_text = "💎 *Premium Plans*\n\n*Your Status:* ❌ Not Active\n\nChoose a plan to unlock Mass DM features:"
                            edit_message(chat_id, msg_id, prem_text, get_premium_menu())
                        elif data.startswith("pay_"):
                            plan_type = data.split("_")[1]
                            upi = get_setting('upi_id')
                            price = get_setting(f'price_{plan_type}')
                            
                            # Real Dynamic QR API link mapping
                            qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=upi://pay?pa={upi}%26am={price}%26cu=INR"
                            
                            pay_caption = (
                                f"💳 **Payment Details**\n\n"
                                f"**Plan:** {plan_type.upper()}\n"
                                f"**Amount:** ₹{price}\n\n"
                                f"⚠️ **PAY ONLY ON THIS QR**\n\n"
                                f"AFTER PAYMENT CLICK PAID ✅ AND SEND:\n"
                                f"• UTR ID\n"
                                f"• PAYMENT SCREENSHOT"
                            )
                            # Deleting template message and pushing official dynamic image
                            requests.post(URL + 'deleteMessage', data={'chat_id': chat_id, 'message_id': msg_id})
                            send_photo(chat_id, qr_api_url, pay_caption, get_payment_action_buttons())
                        elif data == "payment_paid":
                            send_message(chat_id, "✅ **Request Sent!**\n\nPlease send your UTR number or Payment Screenshot here. Admin will approve it instantly.")
                        elif data == "add_session":
                            send_message(chat_id, "📱 **Add Telegram Session**\n\nPlease send your phone number in international format:\nExample: +919876543210")
                            user_steps[chat_id] = 'expecting_phone'
                        elif data == "back_to_menu":
                            requests.post(URL + 'deleteMessage', data={'chat_id': chat_id, 'message_id': msg_id})
                            welcome = "✨ *KUNWAR DMS INCREASER* ✨\n\nChoose an option below."
                            send_photo(chat_id, START_IMAGE_URL, welcome, get_main_menu())
                            
        except Exception as e:
            time.sleep(2)

if __name__ == '__main__':
    Thread(target=run_web_server).start()
    print("Kunwar Core Live with Graphics...")
    bot_polling()
