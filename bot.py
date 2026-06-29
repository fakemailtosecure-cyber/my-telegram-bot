import os
import json
import sqlite3
import requests
import time
from threading import Thread
from flask import Flask, request

app = Flask('')

# ================== CONFIGURATION ==================
TOKEN = '8644302388:AAHQ0PsApaZ6Fv11ezOS45uwAHduzERWBrw'
URL = f'https://api.telegram.org/bot{TOKEN}/'
START_IMAGE_URL = 'https://telegra.ph/file/0c968f94d3a82efda1608.jpg' 
# ===================================================

def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    default_settings = {
        'upi_id': 'sapna513@ptaxis',
        'price_1d': '10', 'price_3d': '25', 'price_7d': '50', 'price_1m': '150', 'price_perm': '299'
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

def get_main_menu():
    return {"inline_keyboard": [
        [{"text": "➕ Add Session", "callback_data": "add_session"}, {"text": "🚀 Start Mass DM", "callback_data": "start_dm"}],
        [{"text": "📊 Check Progress", "callback_data": "check_progress"}, {"text": "💎 Premium Plans", "callback_data": "premium_plans"}],
        [{"text": "🗑️ Logout Session", "callback_data": "logout_session"}, {"text": "📞 Support", "callback_data": "support"}]
    ]}

def get_premium_menu():
    return {"inline_keyboard": [
        [{"text": f"1 Day — ₹{get_setting('price_1d')}", "callback_data": "pay_1d"}],
        [{"text": f"3 Days — ₹{get_setting('price_3d')}", "callback_data": "pay_3d"}],
        [{"text": f"7 Days — ₹{get_setting('price_7d')}", "callback_data": "pay_7d"}],
        [{"text": f"1 Month — ₹{get_setting('price_1m')}", "callback_data": "pay_1m"}],
        [{"text": f"Permanent — ₹{get_setting('price_perm')}", "callback_data": "pay_perm"}],
        [{"text": "⬅️ Back to Menu", "callback_data": "back_to_menu"}]
    ]}

def process_update(update):
    try:
        if "message" in update and "text" in update["message"]:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            text = msg["text"]
            
            if text == "/start":
                welcome = "✨ *KUNWAR DMS INCREASER* ✨\n\n*Server Status:* Online 🟢\n*System:* Active\n*Security:* Enabled\n\nChoose an option below."
                requests.post(URL + 'sendPhoto', json={'chat_id': chat_id, 'photo': START_IMAGE_URL, 'caption': welcome, 'parse_mode': 'Markdown', 'reply_markup': get_main_menu()})
            
            elif text == "/admin":
                # Abhi ke liye bypass lagaya hai taaki aapko panel dikhe aur config handle ho
                admin_text = f"⚙️ *Admin Control Panel*\n\n**Manual UPI:** `{get_setting('upi_id')}`\n\nCommands:\n/setupupi [ID]\n/setprice1d [Price]"
                requests.post(URL + 'sendMessage', json={'chat_id': chat_id, 'text': admin_text, 'parse_mode': 'Markdown'})
                
            elif text.startswith("/setupupi "):
                new_upi = text.split(" ", 1)[1]
                set_setting('upi_id', new_upi)
                requests.post(URL + 'sendMessage', json={'chat_id': chat_id, 'text': f"✅ UPI updated to: `{new_upi}`", 'parse_mode': 'Markdown'})

        elif "callback_query" in update:
            cq = update["callback_query"]
            chat_id = cq["message"]["chat"]["id"]
            msg_id = cq["message"]["message_id"]
            data = cq["data"]
            
            if data == "premium_plans":
                prem_text = "💎 *Premium Plans*\n\nChoose a plan to unlock Mass DM features:"
                requests.post(URL + 'editMessageText', json={'chat_id': chat_id, 'message_id': msg_id, 'text': prem_text, 'parse_mode': 'Markdown', 'reply_markup': get_premium_menu()})
            elif data.startswith("pay_"):
                plan_type = data.split("_")[1]
                upi = get_setting('upi_id')
                price = get_setting(f'price_{plan_type}')
                qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=upi://pay?pa={upi}%26am={price}%26cu=INR"
                
                pay_caption = f"💳 **Payment Details**\n\n**Plan:** {plan_type.upper()}\n**Amount:** ₹{price}\n\n⚠️ **PAY ONLY ON THIS QR**"
                requests.post(URL + 'deleteMessage', json={'chat_id': chat_id, 'message_id': msg_id})
                requests.post(URL + 'sendPhoto', json={'chat_id': chat_id, 'photo': qr_url, 'caption': pay_caption, 'parse_mode': 'Markdown', 'reply_markup': {"inline_keyboard": [[{"text": "PAID ✅", "callback_data": "payment_paid"}, {"text": "CANCEL ❌", "callback_data": "back_to_menu"}]]}})
            elif data == "back_to_menu":
                requests.post(URL + 'deleteMessage', json={'chat_id': chat_id, 'message_id': msg_id})
                requests.post(URL + 'sendPhoto', json={'chat_id': chat_id, 'photo': START_IMAGE_URL, 'caption': "✨ *KUNWAR DMS INCREASER* ✨", 'parse_mode': 'Markdown', 'reply_markup': get_main_menu()})
    except Exception as e:
        print(f"Error: {e}")

# Pure Dynamic Webhook & Polling Hybrid setup
def fallback_polling():
    offset = 0
    while True:
        try:
            r = requests.get(URL + 'getUpdates', params={'offset': offset, 'timeout': 3}).json()
            if "result" in r:
                for update in r["result"]:
                    offset = update["update_id"] + 1
                    process_update(update)
        except: pass
        time.sleep(1)

if __name__ == '__main__':
    Thread(target=fallback_polling).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
