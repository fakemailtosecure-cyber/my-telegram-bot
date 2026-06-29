import os
import json
import sqlite3
import requests
import time
import asyncio
from threading import Thread
from flask import Flask
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

app = Flask('')

@app.route('/')
def home():
    return "Kunwar DMS Core Engine Engine is Online!", 200

# ================== CONFIGURATION ==================
TOKEN = '8644302388:AAEBx4UKSE_e7yjS5j14DHxyXeXS_HJuJUw'
URL = f'https://api.telegram.org/bot{TOKEN}/'
ADMIN_ID = 8644302388  

API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'
# ===================================================

def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY, is_premium INTEGER DEFAULT 0, expiry INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS sessions (chat_id INTEGER, phone TEXT, session_str TEXT)''')
    conn.commit()
    conn.close()

    default_settings = {
        'upi_id': 'sapna513@ptaxis',
        'price_1d': '10', 'price_3d': '25', 'price_7d': '50', 'price_1m': '150', 'price_perm': '299'
    }
    for key, value in default_settings.items():
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
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

def check_premium(chat_id):
    if chat_id == ADMIN_ID: return True
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT is_premium, expiry FROM users WHERE chat_id=?", (chat_id,))
    res = cursor.fetchone()
    conn.close()
    if res and res[0] == 1 and res[1] > int(time.time()):
        return True
    return False

def make_premium(chat_id, days):
    expiry = int(time.time()) + (days * 86400) if days < 999 else int(time.time()) + (9999 * 86400)
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (chat_id, is_premium, expiry) VALUES (?, 1, ?)", (chat_id, expiry))
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

user_states = {}
active_clients = {}
payment_tracking = {}

def send_tg_msg(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup: data['reply_markup'] = json.dumps(reply_markup)
    return requests.post(URL + 'sendMessage', json=data).json()

# THREAD SAFE ASYNC RUNNER FOR LOGIN ENGINE
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

async def init_telethon_login(chat_id, phone):
    session_name = f"session_{chat_id}"
    client = TelegramClient(session_name, API_ID, API_HASH)
    await client.connect()
    try:
        send_code = await client.send_code_request(phone)
        active_clients[chat_id] = {
            'client': client, 'phone': phone, 'phone_code_hash': send_code.phone_code_hash
        }
        user_states[chat_id] = 'expecting_otp'
        send_tg_msg(chat_id, "📩 **OTP Sent!** Please check your Telegram app and type the OTP here.")
    except Exception as e:
        send_tg_msg(chat_id, f"❌ Failed to send OTP: {str(e)}")
        user_states.pop(chat_id, None)
        await client.disconnect()

async def verify_telethon_otp(chat_id, otp):
    data = active_clients.get(chat_id)
    if not data:
        send_tg_msg(chat_id, "❌ Session expired. Please click 'Add Session' again.")
        user_states.pop(chat_id, None)
        return
    client = data['client']
    try:
        await client.sign_in(data['phone'], code=otp, phone_code_hash=data['phone_code_hash'])
        from telethon.sessions import StringSession
        string_session = StringSession.save(client.session)
        
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sessions (chat_id, phone, session_str) VALUES (?, ?, ?)", (chat_id, data['phone'], str(string_session)))
        conn.commit()
        conn.close()
        
        send_tg_msg(chat_id, f"✅ **Session Linked Successfully!**\nNumber: `{data['phone']}`")
        user_states.pop(chat_id, None)
        active_clients.pop(chat_id, None)
    except SessionPasswordNeededError:
        user_states[chat_id] = 'expecting_2fa'
        send_tg_msg(chat_id, "🔒 **2FA Password Required!** Please send your 2-Step Verification password:")
    except Exception as e:
        send_tg_msg(chat_id, f"❌ Login Failed: {str(e)}")
        user_states.pop(chat_id, None)
    finally:
        if user_states.get(chat_id) != 'expecting_2fa':
            await client.disconnect()

async def verify_telethon_2fa(chat_id, password):
    data = active_clients.get(chat_id)
    if not data: return
    client = data['client']
    try:
        await client.sign_in(password=password)
        from telethon.sessions import StringSession
        string_session = StringSession.save(client.session)
        
        conn = sqlite3.connect('bot_data.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sessions (chat_id, phone, session_str) VALUES (?, ?, ?)", (chat_id, data['phone'], str(string_session)))
        conn.commit()
        conn.close()
        
        send_tg_msg(chat_id, "✅ **Logged in with 2FA successfully! Session Linked.**")
        user_states.pop(chat_id, None)
        active_clients.pop(chat_id, None)
    except Exception as e:
        send_tg_msg(chat_id, f"❌ 2FA Verification Failed: {str(e)}")
        user_states.pop(chat_id, None)
    finally:
        await client.disconnect()

def process_update(update):
    try:
        if "message" in update and "text" in update["message"]:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            text = msg["text"]

            # Reset command to break stuck flows
            if text == "/start":
                user_states.pop(chat_id, None)
                welcome = "✨ *KUNWAR DMS INCREASER* ✨\n\nChoose an option below."
                send_tg_msg(chat_id, welcome, get_main_menu())
                return

            # --- ADMIN COMMANDS ---
            if text == "/admin" and chat_id == ADMIN_ID:
                admin_text = f"⚙️ *Admin Panel*\n\nCommands:\n/approve [User_ID] [Days]\n/setupupi [ID]"
                send_tg_msg(chat_id, admin_text)
                return
            elif text.startswith("/approve ") and chat_id == ADMIN_ID:
                parts = text.split(" ")
                target_id = int(parts[1])
                days = int(parts[2])
                make_premium(target_id, days)
                send_tg_msg(ADMIN_ID, f"✅ Approved ID `{target_id}` for {days} days.")
                send_tg_msg(target_id, f"🎉 **Premium Activated!** Admin approved your account.")
                return
            elif text.startswith("/setupupi ") and chat_id == ADMIN_ID:
                new_upi = text.split(" ", 1)[1]
                set_setting('upi_id', new_upi)
                send_tg_msg(chat_id, f"✅ UPI updated: `{new_upi}`")
                return

            # --- USER WORKFLOW STATE LOCKS ---
            if chat_id in user_states:
                state = user_states[chat_id]
                if state == 'expecting_phone':
                    if not text.startswith("+"):
                        send_tg_msg(chat_id, "❌ Include country code. Example: +919876543210")
                        return
                    run_async(init_telethon_login(chat_id, text.strip().replace(" ", "")))
                    return
                elif state == 'expecting_otp':
                    run_async(verify_telethon_otp(chat_id, text.strip()))
                    return
                elif state == 'expecting_2fa':
                    run_async(verify_telethon_2fa(chat_id, text.strip()))
                    return
                elif state == 'expecting_utr':
                    plan = payment_tracking.get(chat_id, "UNKNOWN")
                    user_states.pop(chat_id, None)
                    admin_alert = f"🔔 **NEW VERIFICATION REQUEST!**\n\n👤 User ID: `{chat_id}`\n📦 Plan: {plan.upper()}\n🔢 UTR ID: `{text.strip()}`\n\n⚠️ `/approve {chat_id} 30`"
                    send_tg_msg(ADMIN_ID, admin_alert)
                    send_tg_msg(chat_id, "⏳ **Details Received!** Now please upload the **Payment Screenshot** here. Admin will verify it shortly.")
                    return

        elif "callback_query" in update:
            cq = update["callback_query"]
            chat_id = cq["message"]["chat"]["id"]
            msg_id = cq["message"]["message_id"]
            data = cq["data"]

            if data == "premium_plans":
                prem_text = "💎 *Premium Plans*\n\nChoose a plan to unlock Mass DM tools:"
                requests.post(URL + 'editMessageText', json={'chat_id': chat_id, 'message_id': msg_id, 'text': prem_text, 'parse_mode': 'Markdown', 'reply_markup': get_premium_menu()})
            elif data.startswith("pay_"):
                plan_type = data.split("_")[1]
                upi = get_setting('upi_id')
                price = get_setting(f'price_{plan_type}')
                pay_text = f"💳 **Payment Request**\n\n**Plan:** {plan_type.upper()}\n**Amount:** ₹{price}\n**UPI ID:** `{upi}`\n\n⚠️ **INSTRUCTIONS:**\n1. Pay on the UPI above.\n2. Copy the 12-digit **UTR / Transaction ID**.\n3. Take a **Screenshot**.\n\nClick **PAID ✅** below after payment."
                requests.post(URL + 'editMessageText', json={'chat_id': chat_id, 'message_id': msg_id, 'text': pay_text, 'parse_mode': 'Markdown', 'reply_markup': {"inline_keyboard": [[{"text": "PAID ✅", "callback_data": f"confirm_paid_{plan_type}"}, {"text": "CANCEL ❌", "callback_data": "back_to_menu"}]]}})
            elif data.startswith("confirm_paid_"):
                plan = data.split("_")[2]
                payment_tracking[chat_id] = plan
                user_states[chat_id] = 'expecting_utr'
                requests.post(URL + 'deleteMessage', json={'chat_id': chat_id, 'message_id': msg_id})
                send_tg_msg(chat_id, "✍️ Please enter your **12-digit UTR Number / Transaction ID** here:")
            elif data == "add_session":
                if not check_premium(chat_id):
                    send_tg_msg(chat_id, "❌ **Access Denied!** Buy Premium subscription first.")
                    return
                send_tg_msg(chat_id, "📱 Enter phone number with country code (e.g., `+919876543210`):")
                user_states[chat_id] = 'expecting_phone'
            elif data == "back_to_menu":
                requests.post(URL + 'deleteMessage', json={'chat_id': chat_id, 'message_id': msg_id})
                send_tg_msg(chat_id, "✨ *KUNWAR DMS INCREASER* ✨", get_main_menu())
    except: pass

def run_bot_loop():
    requests.get(URL + 'deleteWebhook')
    offset = 0
    while True:
        try:
            r = requests.get(URL + 'getUpdates', params={'offset': offset, 'timeout': 5}).json()
            if "result" in r:
                for update in r["result"]:
                    offset = update["update_id"] + 1
                    process_update(update)
        except: pass
        time.sleep(1)

if __name__ == '__main__':
    Thread(target=run_bot_loop).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
