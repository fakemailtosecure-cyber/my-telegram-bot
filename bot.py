import os
import json
import requests
import time
from threading import Thread
from flask import Flask, request

app = Flask('')

# ================== CONFIGURATION ==================
TOKEN = '8644302388:AAHB5P1EPHhByrqay9u7hAuWIFt-4jWEIKc'
URL = f'https://api.telegram.org/bot{TOKEN}/'
ADMIN_ID = 6752542323
# ===================================================

DATA_FILE = 'bot_database.json'

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"premium": {}, "sessions": {}, "messages": {}, "stats": {"sent": 0, "failed": 0}}
    try:
        with open(DATA_FILE, 'r') as f: return json.load(f)
    except:
        return {"premium": {}, "sessions": {}, "messages": {}, "stats": {"sent": 0, "failed": 0}}

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

def get_main_menu(chat_id):
    data = load_data()
    msg_set = "✅ Message Set" if str(chat_id) in data["messages"] else "✉️ No Message Set"
    return {"inline_keyboard": [
        [{"text": "🚀 Start Mass DM Campaign", "callback_data": "start_dm_options"}],
        [{"text": "✉️ Set Message", "callback_data": "set_msg"}, {"text": "📋 Preview Message", "callback_data": "preview_msg"}],
        [{"text": "📊 My Stats", "callback_data": "my_stats"}, {"text": "👤 My Account", "callback_data": "my_account"}],
        [{"text": "➕ Add Account", "callback_data": "add_session"}, {"text": "➖ Remove Account", "callback_data": "logout_session"}],
        [{"text": f"Status: {msg_set}", "callback_data": "none"}]
    ]}

def get_target_selection_menu():
    return {"inline_keyboard": [
        [{"text": "BC Usernames List", "callback_data": "target_by_list"}],
        [{"text": "📥 Request Channel", "callback_data": "target_by_requests"}],
        [{"text": "⬅️ Back", "callback_data": "back_to_menu"}]
    ]}

user_states = {}

def send_tg_msg(chat_id, text, reply_markup=None):
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup: payload['reply_markup'] = json.dumps(reply_markup)
    return requests.post(URL + 'sendMessage', json=payload).json()

def process_update(update):
    try:
        if "message" in update:
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            
            if "text" in msg:
                text = msg["text"]
                if text == "/start":
                    user_states.pop(chat_id, None)
                    send_tg_msg(chat_id, "✨ *KUNWAR DMS BOT CORE ENGINE* ✨", get_main_menu(chat_id))
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
            elif data == "start_dm_options":
                if str(chat_id) not in db["messages"]:
                    send_tg_msg(chat_id, "⚠️ Please 'Set Message' first.")
                    return
                requests.post(URL + 'editMessageText', json={'chat_id': chat_id, 'message_id': msg_id, 'text': "🎯 **Select Target Type:**", 'reply_markup': get_target_selection_menu()})
            elif data == "back_to_menu":
                requests.post(URL + 'editMessageText', json={'chat_id': chat_id, 'message_id': msg_id, 'text': "✨ *MAIN PANEL* ✨", 'reply_markup': get_main_menu(chat_id)})
    except: pass

# WEBHOOK ENDPOINT TO EXTINCTION OF DOUBLE MESSAGES
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = json.loads(json_string)
    process_update(update)
    return "!", 200

@app.route('/')
def main_route():
    return "Kunwar DMS Synchronous Engine Active!", 200

def set_webhook_force():
    time.sleep(5)
    # Automatically tracks and bounds url to prevent duplications
    public_url = os.environ.get("RENDER_EXTERNAL_URL")
    if public_url:
        requests.get(URL + f'setWebhook?url={public_url}/{TOKEN}')

if __name__ == '__main__':
    Thread(target=set_webhook_force).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
