import os
import json
import time
import asyncio
import nest_asyncio
from flask import Flask
from threading import Thread
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetChatInviteImportersRequest

nest_asyncio.apply()
app = Flask('')

@app.route('/')
def home():
    return "Kunwar Zerox Ultimate Engine Live!", 200

# ================== CONFIGURATION ==================
TOKEN = '8448000628:AAFW2q8KOvK5T_1jPRP03BfwlsZf_ebSGH4'
ADMIN_ID = 6752542323
API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'
DATA_FILE = 'premium_db.json'
# ===================================================

bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=TOKEN)
user_states = {}
active_clients = {}

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
    return [
        [Button.inline("🚀 Start Mass DM Campaign", b"start_dm_options")],
        [Button.inline("✉️ Set Message", b"set_msg"), Button.inline("📋 Preview Message", b"preview_msg")],
        [Button.inline("📊 My Stats", b"my_stats"), Button.inline("👤 My Account", b"my_account")],
        [Button.inline("👑 VIP Premium", b"premium_plans")],
        [Button.inline("➕ Add Account", b"add_session"), Button.inline("➖ Remove Account", b"logout_session")],
        [Button.inline(f"Campaign Text Status: {msg_status}", b"none")]
    ]

def get_premium_menu():
    return [
        [Button.inline("⚡ 1 Day Access — ₹20", b"pay_1d"), Button.inline("💥 3 Days Access — ₹50", b"pay_3d")],
        [Button.inline("🔥 15 Days Access — ₹100", b"pay_15d"), Button.inline("👑 1 Month Access — ₹150", b"pay_1m")],
        [Button.inline("⬅️ Back to Menu", b"back_to_menu")]
    ]

def get_target_selection_menu():
    return [
        [Button.inline("📝 Target Usernames List", b"target_by_list")],
        [Button.inline("📥 Request Channel / Group", b"target_by_requests")],
        [Button.inline("⬅️ Back to Menu", b"back_to_menu")]
    ]

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    chat_id = event.chat_id
    user_states.pop(chat_id, None)
    text = "✨ **KUNWAR DMS ULTIMATE BOT** ✨\n\nWelcome to elite automation control panel."
    await event.reply(text, buttons=get_main_menu(chat_id))

@bot.on(events.NewMessage(pattern=r'/approve (\d+) (\d+)'))
async def approve_handler(event):
    if event.chat_id != ADMIN_ID: return
    target_id = int(event.pattern_match.group(1))
    days = int(event.pattern_match.group(2))
    make_premium(target_id, days)
    await event.reply(f"✅ Approved `{target_id}` for {days} days.")
    await bot.send_message(target_id, "🎉 Your Premium Plan Activated!")

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    chat_id = event.chat_id
    data = event.data
    db = load_data()
    await event.answer()

    if data == b"back_to_menu":
        user_states.pop(chat_id, None)
        await event.edit("✨ *MAIN PANEL* ✨", buttons=get_main_menu(chat_id))
    elif data == b"set_msg":
        user_states[chat_id] = 'expecting_msg_text'
        await event.respond("📝 Send your message text for campaign:")
    elif data == b"preview_msg":
        msg_text = db["messages"].get(str(chat_id), "❌ No message set yet.")
        await event.respond(f"📋 **Your Message:**\n\n{msg_text}")
    elif data == b"my_stats":
        await event.respond(f"📊 Sent: {db['stats']['sent']} | Failed: {db['stats']['failed']}")
    elif data == b"my_account":
        status = "👑 VIP Premium Active" if check_premium(chat_id) else "❌ Free Tier"
        count = len(db["sessions"].get(str(chat_id), []))
        await event.respond(f"👤 Status: {status}\nLinked Accounts: {count}")
    elif data == b"premium_plans":
        await event.edit("👑 **VIP Premium Plans**", buttons=get_premium_menu())
    elif data in [b"pay_1d", b"pay_3d", b"pay_15d", b"pay_1m"]:
        await event.respond(f"💳 UPI ID: `{db['upi']}`\n\nSend payment and send screenshot below.")
        user_states[chat_id] = 'expecting_screenshot'
    elif data == b"add_session":
        if not check_premium(chat_id):
            await event.respond("❌ **Access Denied!** Premium subscription required.")
            return
        user_states[chat_id] = 'expecting_phone'
        await event.respond("📱 Enter phone number with country code:")
    elif data == b"start_dm_options":
        if not check_premium(chat_id):
            await event.respond("❌ **Access Denied!** Premium subscription required.")
            return
        if str(chat_id) not in db["messages"]:
            await event.respond("⚠️ Please 'Set Message' first.")
            return
        await event.edit("🎯 **Select Target Type:**", buttons=get_target_selection_menu())
    elif data == b"target_by_list":
        user_states[chat_id] = 'expecting_targets'
        await event.respond("📝 Send username list (one username per line):")
    elif data == b"target_by_requests":
        user_states[chat_id] = 'expecting_channel_link'
        await event.respond("📥 Send your channel/group invite link:")
    elif data == b"logout_session":
        if str(chat_id) in db["sessions"]:
            db["sessions"].pop(str(chat_id))
            save_data(db)
            await event.respond("🗑️ All accounts logged out.")
        else:
            await event.respond("❌ No active sessions.")

@bot.on(events.NewMessage)
async def message_input_handler(event):
    if event.text.startswith('/'): return
    chat_id = event.chat_id
    text = event.text.strip()
    
    if chat_id not in user_states: return
    state = user_states[chat_id]

    if state == 'expecting_phone':
        user_states.pop(chat_id, None)
        await event.reply("⏳ Connecting and requesting OTP...")
        loop = asyncio.get_event_loop()
        client = TelegramClient(StringSession(), API_ID, API_HASH, loop=loop)
        await client.connect()
        try:
            send_code = await client.send_code_request(text)
            active_clients[chat_id] = {'client': client, 'phone': text, 'phone_code_hash': send_code.phone_code_hash}
            user_states[chat_id] = 'expecting_otp'
            await event.reply("📩 **OTP Sent!** Telegram app se OTP dekh kar enter karein:")
        except Exception as e:
            await event.reply(f"❌ Failed: {str(e)}")
            await client.disconnect()

    elif state == 'expecting_otp':
        data = active_clients.get(chat_id)
        if not data: return
        user_states.pop(chat_id, None)
        client = data['client']
        try:
            await client.sign_in(data['phone'], code=text, phone_code_hash=data['phone_code_hash'])
            session_str = client.session.save()
            db = load_data()
            if str(chat_id) not in db["sessions"]: db["sessions"][str(chat_id)] = []
            db["sessions"][str(chat_id)].append({"phone": data['phone'], "session": session_str})
            save_data(db)
            await event.reply(f"✅ **Account Linked Successfully!**", buttons=get_main_menu(chat_id))
            active_clients.pop(chat_id, None)
        except Exception as e:
            await event.reply(f"❌ Verification Failed: {str(e)}")
            user_states[chat_id] = 'expecting_otp'
        finally:
            if not active_clients.get(chat_id):
                try: await client.disconnect()
                except: pass

    elif state == 'expecting_msg_text':
        user_states.pop(chat_id, None)
        db = load_data()
        db["messages"][str(chat_id)] = text
        save_data(db)
        await event.reply("✅ **Message Saved Successfully!**", buttons=get_main_menu(chat_id))

    elif state == 'expecting_targets':
        user_states.pop(chat_id, None)
        db = load_data()
        campaign_msg = db["messages"].get(str(chat_id), "")
        user_sessions = db["sessions"].get(str(chat_id), [])
        await event.reply(f"🚀 **Campaign Launched!** Total: {len(text.splitlines())}")
        
        idx = 0
        loop = asyncio.get_event_loop()
        for target in text.splitlines():
            if not target.strip(): continue
            s_info = user_sessions[idx % len(user_sessions)]
            cl = TelegramClient(StringSession(s_info["session"]), API_ID, API_HASH, loop=loop)
            await cl.connect()
            try:
                await cl.send_message(target.strip(), campaign_msg)
                db["stats"]["sent"] += 1
            except:
                db["stats"]["failed"] += 1
            finally:
                try: await cl.disconnect()
                except: pass
            idx += 1
            await asyncio.sleep(2)
        save_data(db)
        await event.reply("✅ **Campaign Completed!**", buttons=get_main_menu(chat_id))

    elif state == 'expecting_screenshot' and event.photo:
        user_states.pop(chat_id, None)
        await event.reply("✅ Screenshot verified! Wait for admin approval.")
        await bot.send_message(ADMIN_ID, f"🔔 **NEW PREMIUM REQUEST**\nID: `{chat_id}`\n\n`/approve {chat_id} 30`")

def start_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

if __name__ == '__main__':
    Thread(target=start_flask, daemon=True).start()
    print("🤖 Telethon Native Engine Active...")
    bot.run_until_disconnected()
