import os
import json
import time
import requests
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Kunwar Zerox Pure Engine Live!", 200

# ================== CONFIGURATION ==================
TOKEN = '8448000628:AAFW2q8KOvK5T_1jPRP03BfwlsZf_ebSGH4'
URL = f'https://api.telegram.org/bot{TOKEN}/'
ADMIN_ID = 6752542323
DATA_FILE = 'premium_db.json'
# ===================================================

user_states = {}
processed_updates = set()
user_click_locks = {}
http_session = requests.Session()

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
    expiry = int(time.time()) + (int(days) * 86400)
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

def get_premium_menu():
    return {"inline_keyboard": [
        [{"text": "⚡ 1 Day Access — ₹20", "callback_data": "pay_1d"}, {"text": "💥 3 Days Access — ₹50", "callback_data": "pay_3d"}],
        [{"text": "🔥 15 Days Access — ₹100", "callback_data": "pay_15d"}, {"text": "👑 1 Month Access — ₹150", "callback_data": "pay_1m"}],
        [{"text": "⬅️ Back to Menu", "callback_data": "back_to_menu"}]
    ]}

def get_target_selection_menu():
    return {"inline_keyboard": [
        [{"text": "📝 Target Usernames List", "callback_data": "target_by_list"}],
        [{"text": "📥 Request Channel / Group", "callback_data": "target_by_requests"}],
        [{"text": "⬅️ Back to Menu", "callback_data": "back_to_menu"}]
    ]}

def answer_callback(callback_query_id):
    try: http_session.post(URL + 'answerCallbackQuery', json={'callback_query_id': callback_query_id})
    except: pass

def send_tg_msg(chat_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup: payload['reply_markup'] = json.dumps(reply_markup)
    try: return http_session.post(URL + 'sendMessage', json=payload).json()
    except: return {}

def edit_tg_msg(chat_id, message_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup: payload['reply_markup'] = json.dumps(reply_markup)
    try: http_session.post(URL + 'editMessageText', json=payload)
    except: pass

def process_update(update):
    try:
        update_id = update.get("update_id")
        if not update_id or update_id in processed_updates:
            return
        processed_updates.add(update_id)

        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            if "text" in msg:
                text = msg["text"].strip()
                if text == "/start":
                    user_states.pop(chat_id, None)
                    send_tg_msg(chat_id, "✨ **KUNWAR DMS ULTIMATE BOT** ✨\n\nWelcome to elite automation control panel.", get_main_menu(chat_id))
                    return
                elif text.startswith("/approve "):
                    if int(chat_id) != int(ADMIN_ID): return
                    parts = text.split(" ")
                    make_premium(int(parts[1]), int(parts[2]))
                    send_tg_msg(ADMIN_ID, f"✅ Approved {parts[1]}")
                    send_tg_msg(int(parts[1]), "🎉 Your Premium Plan Activated!")
                    return

                if chat_id in user_states:
                    state = user_states[chat_id]
                    if state == 'expecting_msg_text':
                        db = load_data()
                        db["messages"][str(chat_id)] = text
                        save_data(db)
                        user_states.pop(chat_id, None)
                        send_tg_msg(chat_id, "✅ **Message Saved Successfully!**", get_main_menu(chat_id))
                        return
                    elif state == 'expecting_phone':
                        user_states.pop(chat_id, None)
                        send_tg_msg(chat_id, "⚙️ Connecting engine to request fresh session OTP layer...")
                        # Standard raw configuration route
                        send_tg_msg(chat_id, "📩 **OTP Request Sent!** Ek baar fresh app log check karke enter karein:")
                        return

            if "photo" in msg and chat_id in user_states and user_states[chat_id] == 'expecting_screenshot':
                photo_id = msg["photo"][-1]["file_id"]
                user_states.pop(chat_id, None)
                send_tg_msg(chat_id, "✅ Screenshot verified! Wait for admin approval.")
                admin_msg = f"🔔 **NEW PREMIUM REQUEST**\nID: `{chat_id}`\n\n`/approve {chat_id} 30`"
                http_session.post(URL + 'sendPhoto', json={'chat_id': ADMIN_ID, 'photo': photo_id, 'caption': admin_msg})
                return

        elif "callback_query" in update:
            cq = update["callback_query"]
            chat_id = cq["message"]["chat"]["id"]
            msg_id = cq["message"]["message_id"]
            data = cq["data"]
            cq_id = cq["id"]
            db = load_data()

            answer_callback(cq_id)

            # Strict Click Interval Barrier
            current_time = time.time()
            if chat_id in user_click_locks and (current_time - user_click_locks[chat_id]) < 2.0:
                return
            user_click_locks[chat_id] = current_time

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
            elif data in ["pay_1d", "pay_3d", "pay_15d", "pay_1m"]:
                edit_tg_msg(chat_id, msg_id, f"💳 UPI ID: `{db['upi']}`\n\nSend payment and send screenshot below.")
                user_states[chat_id] = 'expecting_screenshot'
            elif data == "add_session":
                if not check_premium(chat_id):
                    send_tg_msg(chat_id, "❌ **Access Denied!** Premium subscription required.")
                    return
                user_states[chat_id] = 'expecting_phone'
                send_tg_msg(chat_id, "📱 Enter phone number with country code:")
            elif data == "start_dm_options":
                if not check_premium(chat_id):
                    send_tg_msg(chat_id, "❌ **Access Denied!** Premium subscription required.")
                    return
                if str(chat_id) not in db["messages"]:
                    send_tg_msg(chat_id, "⚠️ Please 'Set Message' first.")
                    return
                edit_tg_msg(chat_id, msg_id, "🎯 **Select Target Type:**", get_target_selection_menu())
            elif data == "back_to_menu":
                user_states.pop(chat_id, None)
                edit_tg_msg(chat_id, msg_id, "✨ *MAIN PANEL* ✨", get_main_menu(chat_id))
    except: pass

def run_bot_loop():
    http_session.get(URL + 'deleteWebhook')
    offset = 0
    while True:
        try:
            r = http_session.get(URL + 'getUpdates', params={'offset': offset, 'timeout': 5}).json()
            if "result" in r:
                for u in r["result"]:
                    offset = u["update_id"] + 1
                    process_update(u)
        except: pass
        time.sleep(1)

if __name__ == '__main__':
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()
    print("🚀 Stable Pure Engine Online...")
    run_bot_loop()
