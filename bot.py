import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from quart import Quart

# --- CONFIGURATION ---
API_ID = 32566844  
API_HASH = '388dd8fd8f08eb03ca2574936c392a4e'  
BOT_TOKEN = '8896611056:AAF9tGjzZ3i7UMZHgT9bbzGG2Ql_JLJ-i2U'  

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = Quart(__name__)

# Storage
user_steps = {}
user_sessions = {}

# --- KEYBOARDS ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="💎 START MASS DM CAMPAIGN", callback_data="start_campaign")
    builder.button(text="🚀 FAST Auto-Forward DM", callback_data="auto_forward")
    builder.button(text="👥 Scrape Group", callback_data="scrape")
    builder.button(text="🤝 Invite & Earn", callback_data="invite")
    builder.button(text="🎀 VIP Premium", callback_data="vip")
    builder.button(text="👤 My Account", callback_data="account")
    builder.button(text="🟢 Add Session", callback_data="add_session")
    builder.button(text="🔴 Remove Session", callback_data="remove_session")
    builder.button(text="🚀 Tutorial & Terms", callback_data="tutorial")
    builder.button(text="💰 Contact Support", callback_data="support")
    builder.adjust(2)
    return builder.as_markup()

# --- COMMANDS & CALLBACKS ---
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    welcome_text = (
        "✨ *Shub DMs Bot* ✨\n"
        "_Premium Mass DM & Marketing Automation_\n\n"
        "Welcome to the most advanced and secure Telegram automation engine. "
        "Maximize your outreach with zero ban risk, utilizing our high-speed smart nodes.\n\n"
        f"👤 *User Profile:* {message.from_user.first_name}\n"
        f"🆔 *Account ID:* `{message.chat.id}`\n"
        "👑 *Server Node:* 🟢 100% Online\n\n"
        "✅ Expand your audience securely!\n"
        "🎁 Claim your *20 Free DMs* trial today."
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_menu())

@dp.callback_query(F.data == "add_session")
async def add_session(call: types.CallbackQuery):
    await call.message.answer("🐱 *Session Generator*\nPlease enter your Telegram Phone Number with country code.\nExample: `+919876543210`", parse_mode="Markdown")
    user_steps[call.message.chat.id] = "WAITING_PHONE"
    await call.answer()

@dp.callback_query(F.data == "start_campaign")
async def start_campaign(call: types.CallbackQuery):
    chat_id = call.message.chat.id
    if chat_id not in user_sessions or not user_sessions[chat_id].get('connected'):
        await call.message.answer("❌ Please add a session/account first using 'Add Session' button.")
        return
    await call.message.answer("👉 *Please send your Target Channel/Group Link.*\nExample: `https://t.me/example`", parse_mode="Markdown")
    user_steps[chat_id] = "WAITING_TARGET"
    await call.answer()

@dp.callback_query(F.data == "vip")
async def vip_menu(call: types.CallbackQuery):
    vip_text = (
        "👑 *VIP Subscription Plans*\n\n"
        "*1 Day:* ₹19 | $\n"
        "*3 Days:* ₹29 | $\n"
        "*7 Days:* ₹39 | $\n"
        "*1 Month:* ₹50 | $\n\n"
        "Select a plan to purchase:"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="💞 1 Day Plan", callback_data="pay_1")
    builder.button(text="💞 3 Days Plan", callback_data="pay_3")
    builder.button(text="💞 7 Days Plan", callback_data="pay_7")
    builder.button(text="💞 1 Month Plan", callback_data="pay_30")
    builder.button(text="🚫 Back", callback_data="back_main")
    builder.adjust(2)
    await call.message.edit_text(vip_text, parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "back_main")
async def back_main(call: types.CallbackQuery):
    await call.message.delete()
    await send_welcome(call.message)

# --- INPUT HANDLING FLOW ---
@dp.message()
async def handle_inputs(message: types.Message):
    chat_id = message.chat.id
    step = user_steps.get(chat_id)
    if not step:
        return

    if step == "WAITING_PHONE":
        phone = message.text.strip()
        user_sessions[chat_id] = {'phone': phone}
        client = TelegramClient(f"session_{chat_id}", API_ID, API_HASH)
        await client.connect()
        try:
            sent_code = await client.send_code_request(phone)
            user_sessions[chat_id]['client'] = client
            user_sessions[chat_id]['phone_code_hash'] = sent_code.phone_code_hash
            await message.answer("📩 *OTP Sent Successfully!*\n\n✅ *Send with spaces:* e.g., `1 2 3 4 5`", parse_mode="Markdown")
            user_steps[chat_id] = "WAITING_OTP"
        except Exception as e:
            await message.answer(f"❌ Error sending OTP: {str(e)}")
            user_steps.pop(chat_id, None)

    elif step == "WAITING_OTP":
        otp = message.text.replace(" ", "").strip()
        session_data = user_sessions.get(chat_id)
        client = session_data['client']
        try:
            await client.sign_in(session_data['phone'], otp, phone_code_hash=session_data['phone_code_hash'])
            await message.answer("✅ *Session Added Successfully!*\nRedirecting to Main Menu...", parse_mode="Markdown")
            user_sessions[chat_id]['connected'] = True
            user_steps.pop(chat_id, None)
        except SessionPasswordNeededError:
            await message.answer("🔒 *Enter your 2FA Password:*", parse_mode="Markdown")
            user_steps[chat_id] = "WAITING_2FA"
        except Exception as e:
            await message.answer(f"❌ OTP verification failed: {str(e)}")
            user_steps.pop(chat_id, None)

    elif step == "WAITING_2FA":
        password = message.text.strip()
        client = user_sessions[chat_id]['client']
        try:
            await client.sign_in(password=password)
            await message.answer("✅ *Session Added Successfully!*\nRedirecting to Main Menu...", parse_mode="Markdown")
            user_sessions[chat_id]['connected'] = True
            user_steps.pop(chat_id, None)
        except Exception as e:
            await message.answer(f"❌ 2FA Password Wrong: {str(e)}")
            user_steps.pop(chat_id, None)

    elif step == "WAITING_TARGET":
        user_sessions[chat_id]['target'] = message.text.strip()
        await message.answer("🔢 *How many DMs do you want to send?* (Send a number)", parse_mode="Markdown")
        user_steps[chat_id] = "WAITING_COUNT"
        
    elif step == "WAITING_COUNT":
        try:
            count = int(message.text.strip())
            target = user_sessions[chat_id]['target']
            await message.answer(f"✅ *Campaign Setup Complete!*\nThe bot will handle the rest in the background. Total targets: `{count}`", parse_mode="Markdown")
            user_steps.pop(chat_id, None)
            asyncio.create_task(run_mass_dm_campaign(chat_id, target, count))
        except ValueError:
            await message.answer("❌ Please enter a valid number.")

# --- DM CAMPAIGN ENGINE ---
async def run_mass_dm_campaign(chat_id, target, total_count):
    client = user_sessions[chat_id]['client']
    try:
        entity = await client.get_entity(target)
        participants = await client.get_participants(entity, limit=total_count)
    except Exception as e:
        await bot.send_message(chat_id, f"❌ Scraping Failed: {str(e)}")
        return

    await bot.send_message(chat_id, f"💎 *Mass DM Started!*\n\n🎯 Target: {target}\n📊 Limit: {total_count}\n🔄 Sessions: 1\n🟢 Filter: All Pending Users", parse_mode="Markdown")
    
    sent, failed = 0, 0
    dm_text = "Hello! Join our official channel for updates."

    for user in participants:
        if user.bot: continue
        try:
            await client.send_message(user.id, dm_text)
            sent += 1
            await asyncio.sleep(15)
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
    await bot.send_message(chat_id, report, parse_mode="Markdown")

# --- WEB SERVER & RUNNER ---
@app.route('/')
async def home():
    return "Bot is Active!"

async def main():
    from hypercorn.config import Config
    from hypercorn.asyncio import serve
    
    config = Config()
    config.bind = [f"0.0.0.0:{os.environ.get('PORT', 8080)}"]
    
    # Run both Web Server and Bot Polling concurrently inside the same event loop
    await asyncio.gather(
        serve(app, config),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
                   
