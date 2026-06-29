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
    return "Kunwar DMS Mega Ultra Engine is fully active and running!", 200

# ================== CONFIGURATION ==================
TOKEN = '8644302388:AAHB5P1EPHhByrqay9u7hAuWIFt-4jWEIKc'
URL = f'https://api.telegram.org/bot{TOKEN}/'
ADMIN_ID = 6752542323  # Thor Bhai Ki ID

API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'
# ===================================================

# DATABASE SYSTEM (JSON BASED FOR RENDER PERSISTENCE)
DATA_FILE = 'bot_database.json'

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"premium": {}, "sessions": {}, "prices": {"1d": "10", "3d": "25", "7d": "50", "1m": "150", "perm": "299"}, "upi": "sapna513@ptaxis"}
    try:
        with open(DATA_FILE, 'r') as f: return json.load(f)
    except:
        return {"premium": {}, "sessions": {}, "prices": {"1d": "10", "3d": "25", "7d": "50", "1m": "150", "perm": "299"}, "upi": "sapna513@ptaxis"}

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

# MAIN INTERFACES
def get_main_menu():
    return {"inline_keyboard": [
        [{"text": "➕ Add Session", "callback_data": "add_session"}, {"text": "🚀 Start Mass DM", "callback_data": "start_dm"}],
        [{"text": "📊 Check Progress", "callback_data": "check_progress"}, {"text": "💎 Premium Plans", "callback_data": "premium_plans"}],
        [{"text": "🗑️ Logout Session", "callback_data": "logout_session"}, {"text": "📞 Support", "callback_data": "support"}]
    ]}

def get_premium_menu():
    data = load_data()
    p = data["prices"]
    return {"inline_keyboard": [
        [{"text": f"1 Day — ₹{p['1d']}", "callback_data": "pay_1d"}],
        [{"text": f"3 Days — ₹{p['3d']}", "callback_data": "pay_3d"}],
        [{"text": f"7 Days — ₹{p['7d']}", "callback_data": "pay_7d"}],
        [{"text": f"1 Month — ₹{p['1m']}", "callback_data": "pay_1m"}],
        [{"text": f"Permanent — ₹{p['perm']}", "callback_data": "pay_perm"}],
        [{"text": "⬅️ Back to Menu", "callback_data": "back_to_menu"}]
    ]}

user_states = {}
active_clients = {}
payment_tracking = {}
dm_progress = {}

def send_tg_msg(chat_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup: payload['reply_markup'] = json.dumps(reply_markup)
    return requests.post(URL + 'sendMessage', json=payload).json()

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try: return loop.run_until_complete(coro)
    finally: loop.close()

# TELETHON LOGIN ENGINE
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
        
        send_tg_msg(chat_id, f"✅ **Session Connected Successfully!**\nNumber: `{data['phone']}`")
        user_states.pop(chat_id, None)
    except SessionPasswordNeededError:
        user_states[chat_id] = 'expecting_2fa'
        send_tg_msg(chat_id, "🔒 **Two-Factor Authentication (2FA) Password enter karein:**")
    except Exception as e:
        send_tg_msg(chat_id, f"❌ Error: {str(e)}")
        user_states.pop(chat_id, None)
    finally:
        if user_states.get(chat_id) != 'expecting_2fa': await client.disconnect()

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
        
        send_tg_msg(chat_id, f"✅ **Session Connected via 2FA Successfully!**\nNumber: `{data['phone']}`")
        user_states.pop(chat_id, None)
    except Exception as e:
        send_tg_msg(chat_id, f"❌ 2FA Failed: {str(e)}")
    finally:
        await client.disconnect()

# AUTOMATIC MASS DM ENGINE
async def start_mass_dm_task(chat_id, usernames, message_text):
    db = load_data()
    user_sessions = db["sessions"].get(str(chat_id), [])
    if not user_sessions:
        send_tg_msg(chat_id, "❌ Aapke paas koi active session nahi hai! Pehle accounts add karein.")
        return

    dm_progress[chat_id] = {"total": len(usernames), "sent": 0, "failed": 0, "status": "Running 🚀"}
    send_tg_msg(chat_id, f"🚀 **Mass DM Progress Started!** Total targets: {len(usernames)}")

    idx = 0
    for target in usernames:
        if not target.strip(): continue
        session_info = user_sessions[idx % len(user_sessions)]
        client = TelegramClient(StringSession(session_info["session"]), API_ID, API_HASH)
        await client.connect()
        try:
            await client.send_message(target.strip(), message_text)
            dm_progress[chat_id]["sent"] += 1
        except:
            dm_progress[chat_id]["failed"] += 1
        finally:
            await client.disconnect()
        idx += 1
        await asyncio.sleep(3) # Safe flood delay

    dm_progress[chat_id]["status"] = "Completed ✅"
    send_tg_msg(chat_id, f"✅ **Mass DM Task Completed!**\nSent: {dm_progress[chat_id]['sent']}\nFailed: {dm_progress[chat_id]['failed']}")

def process_update(update):
    try:
        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            
            if "text" in msg:
                text = msg["text"]
                if text == "/start":
                    user_states.pop(chat_id, None)
                    send_tg_msg(chat_id, "✨ *KUNWAR DMS INCREASER* ✨\n\nChoose an option below to control.", get_main_menu())
                    return

                # ADMIN COMMAND HOOKS
                if text == "/admin" and int(chat_id) == int(ADMIN_ID):
                    send_tg_msg(chat_id, "⚙️ *Admin Control Command Panel*\n\n`/approve USER_ID DAYS`\n`/setupupi NEW_UPI`")
                    return
                elif text.startswith("/approve ") and int(chat_id) == int(ADMIN_ID):
                    parts = text.split(" ")
                    target_user = int(parts[1].strip())
                    target_days = int(parts[2].strip())
                    make_premium(target_user, target_days)
                    send_tg_msg(ADMIN_ID, f"✅ Approved User `{target_user}` for {target_days} Days.")
                    send_tg_msg(target_user, f"🎉 **Premium Subscription Activated!** Admin has approved your account.")
                    return
                elif text.startswith("/setupupi ") and int(chat_id) == int(ADMIN_ID):
                    db = load_data()
                    db["upi"] = text.split(" ", 1)[1].strip()
                    save_data(db)
                    send_tg_msg(chat_id, f"✅ Global UPI updated to: `{db['upi']}`")
                    return

                # USER WORKFLOW STATES
                if chat_id in user_states:
                    state = user_states[chat_id]
                    if state == 'expecting_phone':
                        run_async(init_telethon_login(chat_id, text.strip()))
                        return
                    elif state == 'expecting_otp':
                        run_async(verify_telethon_otp(chat_id, text.strip()))
                        return
                    elif state == 'expecting_2fa':
                        run_async(verify_telethon_2fa(chat_id, text.strip()))
                        return
                    elif state == 'expecting_utr':
                        payment_tracking[chat_id]['utr'] = text.strip()
                        user_states[chat_id] = 'expecting_screenshot'
                        send_tg_msg(chat_id, "⏳ **UTR Saved!** Ab payment ka **Screenshot** yahan upload/send karein:")
                        return
                    elif state == 'expecting_dm_targets':
                        user_states[chat_id] = {'targets': text.splitlines()}
                        send_tg_msg(chat_id, "✍️ Ab woh **Message Text** bhejin jo sabko deliver karna hai:")
                        return
                    elif isinstance(state, dict) and 'targets' in state:
                        targets = state['targets']
                        message_content = text
                        user_states.pop(chat_id, None)
                        Thread(target=lambda: run_async(start_mass_dm_task(chat_id, targets, message_content))).start()
                        return

            # SCREENSHOT SUBMISSION GATEWAY
            if "photo" in msg and chat_id in user_states and user_states[chat_id] == 'expecting_screenshot':
                photo_id = msg["photo"][-1]["file_id"]
                p_data = payment_tracking.get(chat_id, {})
                
                user_states.pop(chat_id, None)
                send_tg_msg(chat_id, "✅ Your details successful verified wait for admin approval")
                
                admin_msg = f"🔔 **NEW PREMIUM APPROVAL REQUEST**\n\n👤 **User ID:** `{chat_id}`\n📦 **Plan:** {p_data.get('plan','').upper()}\n🔢 **UTR:** `{p_data.get('utr','')}`\n\n⚠️ *Click below command to approve:*\n`/approve {chat_id} 30`"
                requests.post(URL + 'sendPhoto', json={'chat_id': ADMIN_ID, 'photo': photo_id, 'caption': admin_msg, 'parse_mode': 'Markdown'})
                return

        elif "callback_query" in update:
            cq = update["callback_query"]
            chat_id = cq["message"]["chat"]["id"]
            msg_id = cq["message"]["message_id"]
            data = cq["data"]

            if data == "premium_plans":
                requests.post(URL + 'editMessageText', json={'chat_id': chat_id, 'message_id': msg_id, 'text': "💎 *Select Premium Subscription Plans*", 'parse_mode': 'Markdown', 'reply_markup': get_premium_menu()})
            elif data.startswith("pay_"):
                db = load_data()
                plan_type = data.split("_")[1]
                pay_text = f"💳 **UPI ID:** `{db['upi']}`\n\nTransfer karne ke baad **PAID ✅** par click karein."
                requests.post(URL + 'editMessageText', json={'chat_id': chat_id, 'message_id': msg_id, 'text': pay_text, 'parse_mode': 'Markdown', 'reply_markup': {"inline_keyboard": [[{"text": "PAID ✅", "callback_data": f"confirm_paid_{plan_type}"}]]}})
            elif data.startswith("confirm_paid_"):
                plan = data.split("_")[2]
                payment_tracking[chat_id] = {'plan': plan}
                user_states[chat_id] = 'expecting_utr'
                requests.post(URL + 'deleteMessage', json={'chat_id': chat_id, 'message_id': msg_id})
                send_tg_msg(chat_id, "✍️ Apna **12-digit UTR Number** enter karein:")
            elif data == "add_session":
                if not check_premium(chat_id):
                    send_tg_msg(chat_id, "❌ **Access Denied!** Pehle premium subscription buy karein.")
                    return
                send_tg_msg(chat_id, "📱 Phone number bhejien (With Country Code, e.g. +91XXXXXXXXXX):")
                user_states[chat_id] = 'expecting_phone'
            elif data == "start_dm":
                if not check_premium(chat_id):
                    send_tg_msg(chat_id, "❌ **Access Denied!** Pehle premium buy karein.")
                    return
                send_tg_msg(chat_id, "🎯 Saare target usernames ki list bhejin (Ek line me ek username):")
                user_states[chat_id] = 'expecting_dm_targets'
            elif data == "check_progress":
                prog = dm_progress.get(chat_id, {"status": "No Active Task 💤", "sent": 0, "failed": 0, "total": 0})
                send_tg_msg(chat_id, f"📊 **Live Task Status:** {prog['status']}\nTotal: {prog['total']}\nSent: {prog['sent']}\nFailed: {prog['failed']}")
            elif data == "logout_session":
                db = load_data()
                if str(chat_id) in db["sessions"]:
                    db["sessions"].pop(str(chat_id), None)
                    save_data(db)
                    send_tg_msg(chat_id, "🗑️ Saare active sessions clear aur logout kar diye gaye hain!")
                else:
                    send_tg_msg(chat_id, "❌ Koi active session nahi mila.")
            elif data == "back_to_menu" or data == "support":
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
