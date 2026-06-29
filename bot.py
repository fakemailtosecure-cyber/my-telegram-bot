import os
import json
import requests
import time
import asyncio
from threading import Thread
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

app = Flask('')

@app.route('/')
def home():
    return "Kunwar DMS Multi-Thread Safe Engine Live!", 200

# ================== CONFIGURATION ==================
TOKEN = '8644302388:AAHB5P1EPHhByrqay9u7hAuWIFt-4jWEIKc'
URL = f'https://api.telegram.org/bot{TOKEN}/'
ADMIN_ID = 6752542323

API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'
# ===================================================

DATA_FILE = 'bot_database.json'

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"premium": {}, "sessions": {}, "messages": {}, "redeem_codes": {"BOOST30DAYS": 30}, "upi": "sapna513@ptaxis", "stats": {"sent": 0, "failed": 0}}
    try:
        with open(DATA_FILE, 'r') as f: return json.load(f)
    except:
        return {"premium": {}, "sessions": {}, "messages": {}, "redeem_codes": {"BOOST30DAYS": 30}, "upi": "sapna513@ptaxis", "stats": {"sent": 0, "failed": 0}}

def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f: json.dump(data, f, indent=4)
    except: pass

def check_premium(chat_id):
    if int(chat_id) == int(ADMIN_ID): return True
    data = load_data()
    if str(chat_id) in data["premium"]:
        if data["premium"][str(chat_id)] > int(time.time()): return True
    return False

def make_premium(chat_id, days):
    data = load_data()
    expiry = int(time.time()) + (int(days) * 86400) if int(days) < 999 else int(time.time()) + (9999 * 86400)
    data["premium"][str(chat_id)] = expiry
    save_data(data)

def get_main_menu(chat_id):
    data = load_data()
    msg_set = "✅ Message Set" if str(chat_id) in data["messages"] else "✉️ No Message Set"
    return {"inline_keyboard": [
        [{"text": "🚀 Start Mass DM Campaign", "callback_data": "start_dm"}],
        [{"text": "✉️ Set Message", "callback_data": "set_msg"}, {"text": "📋 Preview Message", "callback_data": "preview_msg"}],
        [{"text": "📊 My Stats", "callback_data": "my_stats"}, {"text": "👤 My Account", "callback_data": "my_account"}],
        [{"text": "👑 Go VIP Premium", "callback_data": "premium_plans"}, {"text": "🎁 Redeem Code", "callback_data": "redeem_code"}],
        [{"text": "➕ Add Account", "callback_data": "add_session"}, {"text": "➖ Remove Account", "callback_data": "logout_session"}],
        [{"text": "🔗 Refer & Earn", "callback_data": "refer_earn"}],
        [{"text": "📖 How to Use", "callback_data": "how_use"}, {"text": "💬 Support", "callback_data": "support"}],
        [{"text": f"Status: {msg_set}", "callback_data": "none"}]
    ]}

def get_premium_menu():
    return {"inline_keyboard": [
        [{"text": "1 Day — ₹10", "callback_data": "pay_1d"}, {"text": "3 Days — ₹25", "callback_data": "pay_3d"}],
        [{"text": "7 Days — ₹50", "callback_data": "pay_7d"}, {"text": "1 Month — ₹150", "callback_data": "pay_1m"}],
        [{"text": "👑 Permanent VIP — ₹299", "callback_data": "pay_perm"}],
        [{"text": "⬅️ Back to Menu", "callback_data": "back_to_menu"}]
    ]}

user_states = {}
active_clients = {}
payment_tracking = {}

def send_tg_msg(chat_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup: payload['reply_markup'] = json.dumps(reply_markup)
    return requests.post(URL + 'sendMessage', json=payload).json()

# CRITICAL FIX: PURE ISOLATED RUNTIME WORKER FOR TELETHON
def run_telethon_isolated(coro):
    def worker():
        asyncio.run(coro)
    Thread(target=worker).start()

async def init_telethon_login(chat_id, phone):
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    try:
        send_code = await client.send_code_request(phone)
        active_clients[chat_id] = {'client': client, 'phone': phone, 'phone_code_hash': send_code.phone_code_hash}
        user_states[chat_id] = 'expecting_otp'
        send_tg_msg(chat_id, "📩 **OTP Sent!** Apne Telegram app se OTP dekh kar enter karein:")
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
        session_str = client.session.save()
        db = load_data()
        if str(chat_id) not in db["sessions"]: db["sessions"][str(chat_id)] = []
        db["sessions"][str(chat_id)].append({"phone": data['phone'], "session": session_str})
        save_data(db)
        send_tg_msg(chat_id, f"✅ **Account Connected Successfully!**\nPhone: `{data['phone']}`", get_main_menu(chat_id))
        user_states.pop(chat_id, None)
    except SessionPasswordNeededError:
        user_states[chat_id] = 'expecting_2fa'
        send_tg_msg(chat_id, "🔒 **Enter 2FA Password:**")
    except Exception as e:
        send_tg_msg(chat_id, f"❌ Code Error: {str(e)}")
    finally:
        if user_states.get(chat_id) != 'expecting_2fa':
            try: await client.disconnect()
            except: pass

async def verify_telethon_2fa(chat_id, password):
    data = active_clients.get(chat_id)
    if not data: return
    client = data['client']
    try:
        await client.sign_in(password=password)
        session_str = client.session.save()
        db = load_data()
        if str(chat_id) not in db["sessions"]: db["sessions"][str(chat_id)] = []
        db["sessions"][str(chat_id)].append({"phone": data['phone'], "session": session_str})
        save_data(db)
        send_tg_msg(chat_id, f"✅ **Account Linked with 2FA!**", get_main_menu(chat_id))
        user_states.pop(chat_id, None)
    except Exception as e:
        send_tg_msg(chat_id, f"❌ 2FA Incorrect: {str(e)}")
    finally:
        try: await client.disconnect()
        except: pass

async def start_mass_dm_task(chat_id, usernames, message_text):
    db = load_data()
    user_sessions = db["sessions"].get(str(chat_id), [])
    if not user_sessions:
        send_tg_msg(chat_id, "❌ No active session found! Click 'Add Account' first.")
        return
    send_tg_msg(chat_id, f"🚀 **Campaign Launched!**\nTotal targets: {len(usernames)}")
    idx = 0
    for target in usernames:
        if not target.strip(): continue
        s_info = user_sessions[idx % len(user_sessions)]
        client = TelegramClient(StringSession(s_info["session"]), API_ID, API_HASH)
        await client.connect()
        try:
            await client.send_message(target.strip(), message_text)
            db["stats"]["sent"] += 1
        except:
            db["stats"]["failed"] += 1
        finally:
            try: await client.disconnect()
            except: pass
        idx += 1
        await asyncio.sleep(2)
    save_data(db)
    send_tg_msg(chat_id, "✅ **Campaign Completed!** Check 'My Stats' for update.")

def process_update(update):
    try:
        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            
            if "text" in msg:
                text = msg["text"]
                if text == "/start":
                    user_states.pop(chat_id, None)
                    send_tg_msg(chat_id, "✨ *DMS FORWARD BOT CORE* ✨\nYour premium system status verified.", get_main_menu(chat_id))
                    return

                if text == "/admin" and int(chat_id) == int(ADMIN_ID):
                    send_tg_msg(chat_id, "⚙️ *Admin Control Panel*\n\n`/approve USER_ID DAYS`")
                    return
                elif text.startswith("/approve ") and int(chat_id) == int(ADMIN_ID):
                    parts = text.split(" ")
                    make_premium(int(parts[1]), int(parts[2]))
                    send_tg_msg(ADMIN_ID, f"✅ Approved `{parts[1]}`")
                    return

                if chat_id in user_states:
                    state = user_states[chat_id]
                    if state == 'expecting_phone':
                        run_telethon_isolated(init_telethon_login(chat_id, text.strip()))
                        return
                    elif state == 'expecting_otp':
                        run_telethon_isolated(verify_telethon_otp(chat_id, text.strip()))
                        return
                    elif state == 'expecting_2fa':
                        run_telethon_isolated(verify_telethon_2fa(chat_id, text.strip()))
                        return
                    elif state == 'expecting_msg_text':
                        db = load_data()
                        db["messages"][str(chat_id)] = text
                        save_data(db)
                        user_states.pop(chat_id, None)
                        send_tg_msg(chat_id, "✅ **Message Saved Successfully!**", get_main_menu(chat_id))
                        return
                    elif state == 'expecting_targets':
                        db = load_data()
                        campaign_msg = db["messages"].get(str(chat_id), "")
                        user_states.pop(chat_id, None)
                        run_telethon_isolated(start_mass_dm_task(chat_id, text.splitlines(), campaign_msg))
                        return

        elif "callback_query" in update:
            cq = update["callback_query"]
            chat_id = cq["message"]["chat"]["id"]
            msg_id = cq["message"]["message_id"]
            data = cq["data"]
            db = load_data()

            if data == "set_msg":
                user_states[chat_id] = 'expecting_msg_text'
                send_tg_msg(chat_id, "📝 Send your message text for campaign:")
            elif data == "preview_msg":
                msg_text = db["messages"].get(str(chat_id), "❌ No message set yet.")
                send_tg_msg(chat_id, f"📋 **Your Current Campaign Message:**\n\n{msg_text}")
            elif data == "my_stats":
                send_tg_msg(chat_id, f"📊 **Your Campaign Stats:**\nTotal Sent: {db['stats']['sent']}\nTotal Failed: {db['stats']['failed']}")
            elif data == "my_account":
                status = "👑 VIP Premium Active" if check_premium(chat_id) else "❌ Free Tier (Limited)"
                accounts_count = len(db["sessions"].get(str(chat_id), []))
                send_tg_msg(chat_id, f"👤 **Account Info:**\nStatus: {status}\nLinked Accounts: {accounts_count}")
            elif data == "add_session":
                if not check_premium(chat_id):
                    send_tg_msg(chat_id, "❌ **Access Denied!** Buy Premium subscription first.")
                    return
                user_states[chat_id] = 'expecting_phone'
                send_tg_msg(chat_id, "📱 Enter phone number with country code:")
            elif data == "start_dm":
                if not check_premium(chat_id):
                    send_tg_msg(chat_id, "❌ **Access Denied!** Buy Premium subscription first.")
                    return
                if str(chat_id) not in db["messages"]:
                    send_tg_msg(chat_id, "⚠️ Please 'Set Message' first before launching campaign.")
                    return
                user_states[chat_id] = 'expecting_targets'
                send_tg_msg(chat_id, "🎯 Send target list (one username per line):")
            elif data == "logout_session":
                if str(chat_id) in db["sessions"]:
                    db["sessions"].pop(str(chat_id))
                    save_data(db)
                    send_tg_msg(chat_id, "🗑️ All active sessions cleared successfully!")
                else:
                    send_tg_msg(chat_id, "❌ No active sessions found.")
            elif data == "back_to_menu":
                requests.post(URL + 'deleteMessage', json={'chat_id': chat_id, 'message_id': msg_id})
                send_tg_msg(chat_id, "✨ *MAIN PANEL* ✨", get_main_menu(chat_id))
    except: pass

def run_bot_loop():
    requests.get(URL + 'deleteWebhook')
    offset = 0
    while True:
        try:
            r = requests.get(URL + 'getUpdates', params={'offset': offset, 'timeout': 5}).json()
            if "result" in r:
                for u in r["result"]:
                    offset = u["update_id"] + 1
                    process_update(u)
        except: pass
        time.sleep(1)

if __name__ == '__main__':
    Thread(target=run_bot_loop).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
