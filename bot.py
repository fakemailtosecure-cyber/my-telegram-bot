import os
import json
import requests
import time
import asyncio
import nest_asyncio
from flask import Flask
from threading import Thread
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetChatInviteImportersRequest

# 1. Async loop conflict aur background crashes block karne ke liye
nest_asyncio.apply()

app = Flask('')

@app.route('/')
def home():
    return "Zerox DMS Engine Live!", 200

# ================== CONFIGURATION ==================
TOKEN = '8644302388:AAHiYZBwHZVp9puWKyiB3cd_jltw_3Ll_uY'
URL = f'https://api.telegram.org/bot{TOKEN}/'
ADMIN_ID = 6752542323

API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'
DATA_FILE = 'bot_database.json'
# ===================================================

# State control variables (Double message strictly block karne ke liye)
user_states = {}
active_clients = {}
processed_updates = set()

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"premium": {}, "sessions": {}, "messages": {}, "stats": {"sent": 0, "failed": 0}, "upi": "sapna513@ptaxis"}
    try:
        with open(DATA_FILE, 'r') as f: return json.load(f)
    except:
        return {"premium": {}, "sessions": {}, "messages": {}, "stats": {"sent": 0, "failed": 0}, "upi": "sapna513@ptaxis"}

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
    msg_status = "✅ Active" if str(chat_id) in data["messages"] else "❌ Not Set"
    return {"inline_keyboard": [
        [{"text": "🚀 Start Mass DM Campaign", "callback_data": "start_dm_options"}],
        [{"text": "✉️ Set Message", "callback_data": "set_msg"}, {"text": "📋 Preview Message", "callback_data": "preview_msg"}],
        [{"text": "📊 My Stats", "callback_data": "my_stats"}, {"text": "👤 My Account", "callback_data": "my_account"}],
        [{"text": "👑 VIP Premium", "callback_data": "premium_plans"}],
        [{"text": "➕ Add Account", "callback_data": "add_session"}, {"text": "➖ Remove Account", "callback_data": "logout_session"}],
        [{"text": f"Campaign Text Status: {msg_status}", "callback_data": "none"}]
    ]}

def get_target_selection_menu():
    return {"inline_keyboard": [
        [{"text": "📝 Target Usernames List", "callback_data": "target_by_list"}],
        [{"text": "📥 Request Channel / Group", "callback_data": "target_by_requests"}],
        [{"text": "⬅️ Back to Menu", "callback_data": "back_to_menu"}]
    ]}

def get_premium_menu():
    return {"inline_keyboard": [
        [{"text": "1 Month VIP Access — ₹150", "callback_data": "pay_vip"}],
        [{"text": "⬅️ Back to Menu", "callback_data": "back_to_menu"}]
    ]}

def send_tg_msg(chat_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup: payload['reply_markup'] = json.dumps(reply_markup)
    try: return requests.post(URL + 'sendMessage', json=payload).json()
    except: return {}

def edit_tg_msg(chat_id, message_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup: payload['reply_markup'] = json.dumps(reply_markup)
    try: requests.post(URL + 'editMessageText', json=payload)
    except: pass

async def init_telethon_login(chat_id, phone):
    loop = asyncio.get_event_loop()
    client = TelegramClient(StringSession(), API_ID, API_HASH, loop=loop)
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
        send_tg_msg(chat_id, f"✅ **Account Linked Successfully!**", get_main_menu(chat_id))
        user_states.pop(chat_id, None)
        active_clients.pop(chat_id, None)
    except Exception as e:
        send_tg_msg(chat_id, f"❌ Verification Failed: {str(e)}")
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
    
    loop = asyncio.get_event_loop()
    s_info = user_sessions[0]
    client = TelegramClient(StringSession(s_info["session"]), API_ID, API_HASH, loop=loop)
    await client.connect()
    targets = []
    try:
        channel = await client.get_entity(channel_link)
        requests_list = await client(GetChatInviteImportersRequest(peer=channel, requested=True, limit=200))
        for importer in requests_list.importers:
            if importer.user_id: targets.append(importer.user_id)
    except Exception as e:
        send_tg_msg(chat_id, f"❌ Failed to fetch requests: {str(e)}")
        await client.disconnect()
        return
    await client.disconnect()
    
    if not targets:
        send_tg_msg(chat_id, "ℹ️ No pending requests found.")
        return
        
    send_tg_msg(chat_id, f"🎯 Found {len(targets)} requests! Starting Campaign...")
    idx = 0
    for target in targets:
        curr_session = user_sessions[idx % len(user_sessions)]
        cl = TelegramClient(StringSession(curr_session["session"]), API_ID, API_HASH, loop=loop)
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
    send_tg_msg(chat_id, "✅ **Mass DM for Join Requests Completed!**", get_main_menu(chat_id))

async def start_mass_dm_task(chat_id, usernames, message_text):
    db = load_data()
    user_sessions = db["sessions"].get(str(chat_id), [])
    send_tg_msg(chat_id, f"🚀 **Campaign Launched!**\nTotal targets: {len(usernames)}")
    idx = 0
    loop = asyncio.get_event_loop()
    for target in usernames:
        if not target.strip(): continue
        s_info = user_sessions[idx % len(user_sessions)]
        client = TelegramClient(StringSession(s_info["session"]), API_ID, API_HASH, loop=loop)
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
    send_tg_msg(chat_id, "✅ **Campaign Completed Successfully!**", get_main_menu(chat_id))

def process_update(update):
    try:
        # 2. STRICT DOUBLE MESSAGE FIX: Update ID tracking mechanism
        update_id = update.get("update_id")
        if update_id in processed_updates:
            return
        processed_updates.add(update_id)
        if len(processed_updates) > 1000:
            processed_updates.pop() # Buffer overflow protection

        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            if "text" in msg:
                text = msg["text"].strip()
                if text == "/start":
                    user_states.pop(chat_id, None)
                    send_tg_msg(chat_id, "✨ **KUNWAR DMS ULTIMATE BOT** ✨\n\nWelcome to elite automation control panel.", get_main_menu(chat_id))
                    return
                if text == "/admin" and int(chat_id) == int(ADMIN_ID):
                    send_tg_msg(chat_id, "⚙️ Admin Option: `/approve USER_ID DAYS`")
                    return
                elif text.startswith("/approve ") and int(chat_id) == int(ADMIN_ID):
                    parts = text.split(" ")
                    make_premium(int(parts[1]), int(parts[2]))
                    send_tg_msg(ADMIN_ID, f"✅ Approved `{parts[1]}`")
                    send_tg_msg(int(parts[1]), "🎉 Your Premium Plan Activated!")
                    return

                if chat_id in user_states:
                    state = user_states[chat_id]
                    if state == 'expecting_phone':
                        asyncio.create_task(init_telethon_login(chat_id, text))
                        return
                    elif state == 'expecting_otp':
                        asyncio.create_task(verify_telethon_otp(chat_id, text))
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
                        asyncio.create_task(start_mass_dm_task(chat_id, text.splitlines(), campaign_msg))
                        return
                    elif state == 'expecting_channel_link':
                        db = load_data()
                        campaign_msg = db["messages"].get(str(chat_id), "")
                        user_states.pop(chat_id, None)
                        asyncio.create_task(scrape_and_dm_join_requests(chat_id, text, campaign_msg))
                        return
            
            if "photo" in msg and chat_id in user_states and user_states[chat_id] == 'expecting_screenshot':
                photo_id = msg["photo"][-1]["file_id"]
                user_states.pop(chat_id, None)
                send_tg_msg(chat_id, "✅ Your details successful verified wait for admin approval")
                admin_msg = f"🔔 **NEW REQUEST**\nID: `{chat_id}`\n\n`/approve {chat_id} 30`"
                requests.post(URL + 'sendPhoto', json={'chat_id': ADMIN_ID, 'photo': photo_id, 'caption': admin_msg})
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
                count = len(db["sessions"].get(str(chat_id), []))
                send_tg_msg(chat_id, f"👤 Status: {status}\nLinked Accounts: {count}")
            elif data == "premium_plans":
                edit_tg_msg(chat_id, msg_id, "👑 **VIP Premium Plans**", get_premium_menu())
            elif data == "pay_vip":
                edit_tg_msg(chat_id, msg_id, f"💳 UPI ID: `{db['upi']}`\n\nSend payment and send screenshot below.")
                user_states[chat_id] = 'expecting_screenshot'
            elif data == "add_session":
                if not check_premium(chat_id):
                    send_tg_msg(chat_id, "❌ **Access Denied!** Buy Premium subscription first.")
                    return
                user_states[chat_id] = 'expecting_phone'
                send_tg_msg(chat_id, "📱 Enter phone number with country code:")
            elif data == "start_dm_options":
                if not check_premium(chat_id):
                    send_tg_msg(chat_id, "❌ **Access Denied!** Buy Premium subscription first.")
                    return
                if str(chat_id) not in db["messages"]:
                    send_tg_msg(chat_id, "⚠️ Please 'Set Message' first.")
                    return
                edit_tg_msg(chat_id, msg_id, "🎯 **Select Target Type:**", get_target_selection_menu())
            elif data == "target_by_list":
                user_states[chat_id] = 'expecting_targets'
                send_tg_msg(chat_id, "📝 Send username list (one username per line):")
            elif data == "target_by_requests":
                user_states[chat_id] = 'expecting_channel_link'
                send_tg_msg(chat_id, "📥 Apne channel ka link ya username bhejein:")
            elif data == "logout_session":
                if str(chat_id) in db["sessions"]:
                    db["sessions"].pop(str(chat_id))
                    save_data(db)
                    send_tg_msg(chat_id, "🗑️ All accounts logged out.")
                else:
                    send_tg_msg(chat_id, "❌ No active sessions found.")
            elif data == "back_to_menu":
                edit_tg_msg(chat_id, msg_id, "✨ *MAIN PANEL* ✨", get_main_menu(chat_id))
    except: pass

async def run_bot_loop():
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
        await asyncio.sleep(1)

def start_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == '__main__':
    Thread(target=start_flask, daemon=True).start()
    print("🤖 Zerox DMS System Loaded Perfectly...")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_bot_loop())
