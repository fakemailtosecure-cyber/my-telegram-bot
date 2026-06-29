import os
import json
import requests
import time
import asyncio
from threading import Thread
from flask import Flask
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetChatInviteImportersRequest

app = Flask('')

@app.route('/')
def home():
    return "Kunwar DMS Mega Hybrid Engine Live!", 200

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
        [{"text": "🚀 Start Mass DM Campaign", "callback_data": "start_dm_options"}],
        [{"text": "✉️ Set Message", "callback_data": "set_msg"}, {"text": "📋 Preview Message", "callback_data": "preview_msg"}],
        [{"text": "📊 My Stats", "callback_data": "my_stats"}, {"text": "👤 My Account", "callback_data": "my_account"}],
        [{"text": "👑 Go VIP Premium", "callback_data": "premium_plans"}, {"text": "🎁 Redeem Code", "callback_data": "redeem_code"}],
        [{"text": "➕ Add Account", "callback_data": "add_session"}, {"text": "➖ Remove Account", "callback_data": "logout_session"}],
        [{"text": "🔗 Refer & Earn", "callback_data": "refer_earn"}],
        [{"text": "📖 How to Use", "callback_data": "how_use"}, {"text": "💬 Support", "callback_data": "support"}],
        [{"text": f"Status: {msg_set}", "callback_data": "none"}]
    ]}

def get_target_selection_menu():
    return {"inline_keyboard": [
        [{"text": "📝 Target Usernames List", "callback_data": "target_by_list"}],
        [{"text": "📥 Request Channel / Group", "callback_data": "target_by_requests"}],
        [{"text": "⬅️ Back to Menu", "callback_data": "back_to_menu"}]
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
        send_tg_msg(chat_id, f"✅ **Account Connected Successfully!**", get_main_menu(chat_id))
        user_states.pop(chat_id, None)
    except:
        send_tg_msg(chat_id, "❌ Verification Failed.")
    finally:
        try: await client.disconnect()
        except: pass

async def scrape_and_dm_join_requests(chat_id, channel_link, message_text):
    db = load_data()
    user_sessions = db["sessions"].get(str(chat_id), [])
    if not user_sessions:
        send_tg_msg(chat_id, "❌ No active session found! Click 'Add Account' first.")
        return
        
    send_tg_msg(chat_id, "⏳ Fetching pending join requests from channel/group...")
    s_info = user_sessions[0]
    client = TelegramClient(StringSession(s_info["session"]), API_ID, API_HASH)
    await client.connect()
    
    targets = []
    try:
        channel = await client.get_entity(channel_link)
        requests_list = await client(GetChatInviteImportersRequest(peer=channel, requested=True, limit=100))
        for importer in requests_list.importers:
            if importer.user_id:
                targets.append(importer.user_id)
    except Exception as e:
        send_tg_msg(chat_id, f"❌ Failed to fetch requests: {str(e)}")
        await client.disconnect()
        return
        
    await client.disconnect()
    
    if not targets:
        send_tg_msg(chat_id, "ℹ️ Koi pending join requests nahi mili is channel par.")
        return
        
    send_tg_msg(chat_id, f"🎯 Found {len(targets)} pending requests! Starting Mass DM...")
    idx = 0
    for target in targets:
        curr_session = user_sessions[idx % len(user_sessions)]
        cl = TelegramClient(StringSession(curr_session["session"]), API_ID, API_HASH)
        await cl.connect()
        try:
            await cl.send_message(target, message_text)
            db["stats"]["sent"] += 1
        except:
            db["stats"]["failed"] += 1
        finally:
            try: await cl.disconnect()
            except: pass
        idx += 1
        await asyncio.sleep(2)
        
    save_data(db)
    send_tg_msg(chat_id, "✅ **Join Request Mass DM Completed!**")

async def start_mass_dm_task(chat_id, usernames, message_text):
    db = load_data()
    user_sessions = db["sessions"].get(str(chat_id), [])
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
    send_tg_msg(chat_id, "✅ **Campaign Completed!**")

def process_update(update):
    try:
        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            
            if "text" in msg:
                text = msg["text"]
                if text == "/start":
                    user_states.pop(chat_id, None)
                    send_tg_msg(chat_id, "✨ *DMS FORWARD BOT HYBRID* ✨", get_main_menu(chat_id))
                    return

                if text == "/admin" and int(chat_id) == int(ADMIN_ID):
                    send_tg_msg(chat_id, "⚙️ Admin Option: `/approve USER_ID DAYS`")
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
                    elif state == 'expecting_channel_link':
                        db = load_data()
                        campaign_msg = db["messages"].get(str(chat_id), "")
                        user_states.pop(chat_id, None)
                        run_telethon_isolated(scrape_and_dm_join_requests(chat_id, text.strip(), campaign_msg))
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
                send_tg_msg(chat_id, f"📋 **Your Message:**\n\n{msg_text}")
            elif data == "my_stats":
                send_tg_msg(chat_id, f"📊 Sent: {db['stats']['sent']} | Failed: {db['stats']['failed']}")
            elif data == "my_account":
                status = "👑 VIP Premium Active" if check_premium(chat_id) else "❌ Free Tier"
                send_tg_msg(chat_id, f"👤 Status: {status}")
            elif data == "add_session":
                user_states[chat_id] = 'expecting_phone'
                send_tg_msg(chat_id, "📱 Enter phone number with country code:")
            elif data == "start_dm_options":
                if not check_premium(chat_id):
                    send_tg_msg(chat_id, "❌ **Access Denied!** Buy Premium subscription first.")
                    return
                if str(chat_id) not in db["messages"]:
                    send_tg_msg(chat_id, "⚠️ Please 'Set Message' first.")
                    return
                requests.post(URL + 'editMessageText', json={'chat_id': chat_id, 'message_id': msg_id, 'text': "🎯 **Select Campaign Target Type:**", 'reply_markup': get_target_selection_menu()})
            elif data == "target_by_list":
                user_states[chat_id] = 'expecting_targets'
                send_tg_msg(chat_id, "📝 Send username list (one username per line):")
            elif data == "target_by_requests":
                user_states[chat_id] = 'expecting_channel_link'
                send_tg_msg(chat_id, "📥 Apne public/private channel ka link ya username bhejein:")
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
