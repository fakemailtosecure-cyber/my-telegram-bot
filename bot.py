import requests
import time
import json
import os
from threading import Thread
from flask import Flask

# Hosting server ko active rakhne ke liye chota web server
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Aapka Telegram Bot Token
TOKEN = '8644302388:AAHQ0PsApaZ6Fv11ezOS45uwAHduzERWBrw'
URL = f'https://api.telegram.org/bot{TOKEN}/'

def get_main_menu():
    return {
        "inline_keyboard": [
            [{"text": "➕ Add Session", "callback_data": "add_session"}, {"text": "🚀 Start Mass DM", "callback_data": "start_dm"}],
            [{"text": "📊 Check Progress", "callback_data": "check_progress"}, {"text": "💎 Premium Plans", "callback_data": "premium_plans"}],
            [{"text": "🗑️ Logout Session", "callback_data": "logout_session"}, {"text": "📞 Support", "callback_data": "support"}]
        ]
    }

def get_premium_menu():
    return {
        "inline_keyboard": [
            [{"text": "1 Day — ₹10", "callback_data": "plan_1d"}],
            [{"text": "3 Days — ₹25", "callback_data": "plan_3d"}],
            [{"text": "7 Days — ₹50", "callback_data": "plan_7d"}],
            [{"text": "1 Month — ₹150", "callback_data": "plan_1m"}],
            [{"text": "Permanent — ₹299", "callback_data": "plan_perm"}],
            [{"text": "⬅️ Back to Menu", "callback_data": "back_to_menu"}]
        ]
    }

def send_message(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    requests.post(URL + 'sendMessage', data=data)

def edit_message(chat_id, message_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': 'Markdown'}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    requests.post(URL + 'editMessageText', data=data)

def answer_callback(callback_query_id, text):
    requests.post(URL + 'answerCallbackQuery', data={'callback_query_id': callback_query_id, 'text': text, 'show_alert': True})

def bot_polling():
    offset = 0
    while True:
        try:
            r = requests.get(URL + 'getUpdates', params={'offset': offset, 'timeout': 1}).json()
            if "result" in r:
                for update in r["result"]:
                    offset = update["update_id"] + 1
                    if "message" in update and "text" in update["message"]:
                        msg = update["message"]
                        if msg["text"] == "/start":
                            welcome = "✨ *KUNWAR DMS INCREASER* ✨\n\n*Server Status:* Online 🟢\n*System:* Active\n*Security:* Enabled\n\nChoose an option below."
                            send_message(msg["chat"]["id"], welcome, get_main_menu())
                    elif "callback_query" in update:
                        cq = update["callback_query"]
                        chat_id = cq["message"]["chat"]["id"]
                        msg_id = cq["message"]["message_id"]
                        data = cq["data"]
                        if data == "premium_plans":
                            prem = "💎 *Premium Plans*\n\n*Your Status:* ❌ Not Active\n\nChoose a plan to unlock Mass DM features:\n\n1️⃣ 1 Day — ₹10\n2️⃣ 3 Days — ₹25\n3️⃣ 7 Days — ₹50\n4️⃣ 1 Month — ₹150\n5️⃣ Permanent — ₹299"
                            edit_message(chat_id, msg_id, prem, get_premium_menu())
                        elif data == "back_to_menu":
                            welcome = "✨ *KUNWAR DMS INCREASER* ✨\n\n*Server Status:* Online 🟢\n*System:* Active\n*Security:* Enabled\n\nChoose an option below."
                            edit_message(chat_id, msg_id, welcome, get_main_menu())
                        else:
                            answer_callback(cq["id"], f"Aapne select kiya: {data}")
        except Exception as e:
            pass
        time.sleep(0.1)

if __name__ == '__main__':
    Thread(target=run_web_server).start()
    print("Bot chalu ho raha hai...")
    bot_polling()
