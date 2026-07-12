import os
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- CONFIGURATION (Aapke Credentials Yahan Add Kar Diye Hain) ---
API_ID = 32566844  
API_HASH = '388dd8fd8f08eb03ca2574936c392a4e'  
BOT_TOKEN = '8896611056:AAF9tGjzZ3i7UMZHgT9bbzGG2Ql_JLJ-i2U'  

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# Temporary in-memory storage
user_steps = {}
user_sessions = {}  
active_campaigns = {} 

# --- KEYBOARDS ---
def get_main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("💎 START MASS DM CAMPAIGN", callback_data="start_campaign"),
        InlineKeyboardButton("🚀 FAST Auto-Forward DM", callback_data="auto_forward")
    )
    markup.add(
        InlineKeyboardButton("👥 Scrape Group", callback_data="scrape"),
        InlineKeyboardButton("🤝 Invite & Earn", callback_data="invite")
    )
    markup.add(
        InlineKeyboardButton("🎀 VIP Premium", callback_data="vip"),
        InlineKeyboardButton("👤 My Account", callback_data="account")
    )
    markup.add(
        InlineKeyboardButton("🟢 Add Session", callback_data="add_session"),
        InlineKeyboardButton("🔴 Remove Session", callback_data="remove_session")
    )
    markup.add(
        InlineKeyboardButton("🚀 Tutorial & Terms", callback_data="tutorial"),
        InlineKeyboardButton("💰 Contact Support", callback_data="support")
    )
    return markup

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    welcome_text = (
        "✨ *Shub DMs Bot* ✨\n"
        "_Premium Mass DM & Marketing Automation_\n\n"
        "Welcome to the most advanced and secure Telegram automation engine. "
        "Maximize your outreach with zero ban risk, utilizing our high-speed smart nodes.\n\n"
        f"👤 *User Profile:* {message.from_user.first_name}\n"
        f"🆔 *Account ID:* `{chat_id}`\n"
        "👑 *Server Node:* 🟢 100% Online\n\n"
        "✅ Expand your audience securely!\n"
        "🎁 Claim your *20 Free DMs* trial today."
    )
    bot.send_message(chat_id, welcome_text, reply_markup=get_main_menu())

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    
    if call.data == "add_session":
        bot.send_message(chat_id, "🐱 *Session Generator*\nPlease enter your Telegram Phone Number with country code.\nExample: `+919876543210`")
        user_steps[chat_id] = "WAITING_PHONE"
        
    elif call.data == "start_campaign":
        if chat_id not in user_sessions or not user_sessions[chat_id].get('connected'):
            bot.send_message(chat_id, "❌ Please add a session/account first using 'Add Session' button.")
            return
        bot.send_message(chat_id, "👉 *Please send your Target Channel/Group Link.*\nExample: `https://t.me/example`")
        user_steps[chat_id] = "WAITING_TARGET"
        
    elif call.data == "vip":
        vip_text = (
            "👑 *VIP Subscription Plans*\n\n"
            "*1 Day:* ₹19 | $\n"
            "*3 Days:* ₹29 | $\n"
            "*7 Days:* ₹39 | $\n"
            "*1 Month:* ₹50 | $\n\n"
            "Select a plan to purchase:"
        )
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("💞 1 Day Plan", callback_data="pay_1"),
            InlineKeyboardButton("💞 3 Days Plan", callback_data="pay_3"),
            InlineKeyboardButton("💞 7 Days Plan", callback_data="pay_7"),
            InlineKeyboardButton("💞 1 Month Plan", callback_data="pay_30")
        )
        markup.add(InlineKeyboardButton("🚫 Back", callback_data="back_main"))
        bot.edit_message_text(vip_text, chat_id, call.message.message_id, reply_markup=markup)
        
    elif call.data == "back_main":
        send_welcome(call.message)

# --- TEXT INPUT FLOW ---
@bot.message_handler(func=lambda message: message.chat.id in user_steps)
def handle_inputs(message):
    chat_id = message.chat.id
    step = user_steps.get(chat_id)
    
    if step == "WAITING_PHONE":
        phone = message.text.strip()
        user_sessions[chat_id] = {'phone': phone}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        client = TelegramClient(f"session_{chat_id}", API_ID, API_HASH)
        loop.run_until_complete(client.connect())
        
        try:
            sent_code = loop.run_until_complete(client.send_code_request(phone))
            user_sessions[chat_id]['client'] = client
            user_sessions[chat_id]['phone_code_hash'] = sent_code.phone_code_hash
            
            bot.send_message(chat_id, "📩 *OTP Sent Successfully!*\n\n✅ *Send with spaces:* e.g., `1 2 3 4 5`")
            user_steps[chat_id] = "WAITING_OTP"
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error sending OTP: {str(e)}")
            user_steps.pop(chat_id, None)

    elif step == "WAITING_OTP":
        otp = message.text.replace(" ", "").strip()
        session_data = user_sessions.get(chat_id)
        client = session_data['client']
        phone = session_data['phone']
        phone_code_hash = session_data['phone_code_hash']
        
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(client.sign_in(phone, otp, phone_code_hash=phone_code_hash))
            bot.send_message(chat_id, "✅ *Session Added Successfully!*\nRedirecting to Main Menu...")
            user_sessions[chat_id]['connected'] = True
            user_steps.pop(chat_id, None)
        except SessionPasswordNeededError:
            bot.send_message(chat_id, "🔒 *Enter your 2FA Password:*")
            user_steps[chat_id] = "WAITING_2FA"
        except Exception as e:
            bot.send_message(chat_id, f"❌ OTP verification failed: {str(e)}")
            user_steps.pop(chat_id, None)

    elif step == "WAITING_2FA":
        password = message.text.strip()
        session_data = user_sessions.get(chat_id)
        client = session_data['client']
        
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(client.sign_in(password=password))
            bot.send_message(chat_id, "✅ *Session Added Successfully!*\nRedirecting to Main Menu...")
            user_sessions[chat_id]['connected'] = True
            user_steps.pop(chat_id, None)
        except Exception as e:
            bot.send_message(chat_id, f"❌ 2FA Password Wrong: {str(e)}")
            user_steps.pop(chat_id, None)

    elif step == "WAITING_TARGET":
        target = message.text.strip()
        user_sessions[chat_id]['target'] = target
        bot.send_message(chat_id, "🔢 *How many DMs do you want to send?* (Send a number)")
        user_steps[chat_id] = "WAITING_COUNT"
        
    elif step == "WAITING_COUNT":
        try:
            count = int(message.text.strip())
            session_data = user_sessions.get(chat_id)
            target = session_data['target']
            
            bot.send_message(chat_id, f"✅ *Campaign Setup Complete!*\nThe bot will handle the rest in the background. Total targets: `{count}`")
            user_steps.pop(chat_id, None)
            
            asyncio.run(run_mass_dm_campaign(chat_id, target, count))
        except ValueError:
            bot.send_message(chat_id, "❌ Please enter a valid number.")

# --- BACKGROUND AUTOMATION ENGINE ---
async def run_mass_dm_campaign(chat_id, target, total_count):
    session_data = user_sessions.get(chat_id)
    client = session_data['client']
    
    try:
        entity = await client.get_entity(target)
        participants = await client.get_participants(entity, limit=total_count)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Scraping Failed: {str(e)}")
        return

    bot.send_message(chat_id, f"💎 *Mass DM Started!*\n\n🎯 Target: {target}\n📊 Limit: {total_count}\n🔄 Sessions: 1\n🟢 Filter: All Pending Users")
    
    sent = 0
    failed = 0
    dm_text = "Hello! Join our official channel for latest updates."

    for user in participants:
        if user.bot:
            continue
        try:
            await client.send_message(user.id, dm_text)
            sent += 1
            await asyncio.sleep(15) # Anti-ban delay
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
        except Exception:
            failed += 1
            
    report = (
        "📊 *Post-Campaign Analytics Report*\n\n"
        f"🎯 Target: {target}\n"
        f"✅ Successfully Queued/Sent: {sent}\n"
        f"❌ Failed Blocks: {failed}\n\n"
        "🚪 *Security:* _Your Telegram session remains active securely._"
    )
    bot.send_message(chat_id, report)

# --- START BOT ---
if __name__ == "__main__":
    print("🤖 Bot is pooling...")
    bot.infinity_polling()
        
