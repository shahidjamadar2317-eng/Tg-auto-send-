import asyncio
import os
import threading
import time
from datetime import datetime
from collections import defaultdict
from flask import Flask
from pyrogram import Client, filters

# ---------- Environment Variables ----------
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# ---------- Rate Limiting Setup ----------
user_last_command = defaultdict(float)

def rate_limit(user_id, cooldown=3):
    """3 seconds cooldown between commands"""
    current_time = time.time()
    if current_time - user_last_command[user_id] < cooldown:
        return False
    user_last_command[user_id] = current_time
    return True

# ---------- Flask App ----------
server = Flask(__name__)

# ---------- Config Store ----------
spam_config = {
    "chat_id": None,
    "message": "Hello from Userbot! 🚀",
    "interval": 30,
    "is_running": False
}

# ---------- Clients ----------
bot = Client("control_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client("user_account", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ---------- Logger Function ----------
def log_command(user_id, command):
    """Log all commands to file"""
    try:
        with open("command_logs.txt", "a") as f:
            f.write(f"{datetime.now()} | User: {user_id} | Command: {command}\n")
    except:
        pass

# ---------- Spam Worker ----------
async def spam_worker():
    """Background loop jo lagatar check karega aur message bhejega"""
    while True:
        if spam_config["is_running"] and spam_config["chat_id"]:
            try:
                await user.send_message(spam_config["chat_id"], spam_config["message"])
                print(f"[+] User account sent message to {spam_config['chat_id']}")
            except Exception as e:
                print(f"[-] Spam Error: {e}")
            
            await asyncio.sleep(spam_config["interval"])
        else:
            await asyncio.sleep(1)

# ---------- Owner Only Decorator ----------
def owner_only(func):
    """Custom decorator for owner-only commands with extra security"""
    async def wrapper(client, message):
        # Check 1: Only owner
        if message.from_user.id != OWNER_ID:
            await message.reply("❌ You are not authorized to use this bot!")
            return
        
        # Check 2: Only private chat
        if message.chat.type != "private":
            await message.reply("❌ Use this bot in private chat only!")
            return
        
        # Check 3: Rate limit
        if not rate_limit(message.from_user.id):
            await message.reply("⏳ Slow down! Wait 3 seconds between commands.")
            return
        
        # Log the command
        log_command(message.from_user.id, message.text)
        
        return await func(client, message)
    return wrapper

# ---------- Bot Commands ----------
@bot.on_message(filters.command(["start", "help"]))
@owner_only
async def start_command(client, message):
    help_text = (
        "🤖 Userbot Controller Active!\n\n"
        "📌 Commands:\n"
        "/setgroup <ID/Username/Link> - Target group set karein\n"
        "/setmsg <text> - Prank text set karein\n"
        "/settime <seconds> - Time interval set karein\n"
        "/status - Current configuration dekhein\n"
        "/start_spam - Spamming shuru karein\n"
        "/stop_spam - Spamming rok dein\n\n"
        "🔐 Only authorized owner can use this bot!"
    )
    await message.reply_text(help_text)

@bot.on_message(filters.command("setgroup"))
@owner_only
async def set_group(client, message):
    try:
        group = message.text.split(maxsplit=1)[1]
        if "t.me/" in group:
            group = group.split("t.me/")[1]
        if not group.startswith("@"):
            group = f"@{group}"
        
        spam_config["chat_id"] = group
        await message.reply_text(f"✅ Target Group Set: `{group}`")
    except IndexError:
        await message.reply_text("❌ Format: `/setgroup @groupusername` ya `/setgroup -100xxxxxxx`")

@bot.on_message(filters.command("setmsg"))
@owner_only
async def set_msg(client, message):
    try:
        msg_text = message.text.split(maxsplit=1)[1]
        spam_config["message"] = msg_text
        await message.reply_text(f"✅ Message text set to:\n{msg_text}")
    except IndexError:
        await message.reply_text("❌ Format: /setmsg Tera text yahan")

@bot.on_message(filters.command("settime"))
@owner_only
async def set_time(client, message):
    try:
        seconds = int(message.text.split(maxsplit=1)[1])
        if seconds < 10:
            await message.reply_text("⚠️ Account safety ke liye minimal 10 seconds rakhein.")
            return
        spam_config["interval"] = seconds
        await message.reply_text(f"✅ Interval Set: {seconds} seconds")
    except (IndexError, ValueError):
        await message.reply_text("❌ Format: /settime 30")

@bot.on_message(filters.command("status"))
@owner_only
async def status(client, message):
    status_msg = (
        f"📊 Current Status:\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Target Chat: `{spam_config['chat_id']}`\n"
        f"Message: `{spam_config['message']}`\n"
        f"Interval: `{spam_config['interval']}s`\n"
        f"Running: `{'✅ YES' if spam_config['is_running'] else '❌ NO'}`\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Owner: `{OWNER_ID}`"
    )
    await message.reply_text(status_msg)

@bot.on_message(filters.command("start_spam"))
@owner_only
async def start_spam(client, message):
    if not spam_config["chat_id"]:
        await message.reply_text("❌ Pehle /setgroup set karo!")
        return
    
    if not spam_config["is_running"]:
        spam_config["is_running"] = True
        await message.reply_text("🚀 Tumhare account se background spamming shuru ho chuki hai!")
    else:
        await message.reply_text("⚠️ Spammer pehle se hi chal raha hai.")

@bot.on_message(filters.command("stop_spam"))
@owner_only
async def stop_spam(client, message):
    if spam_config["is_running"]:
        spam_config["is_running"] = False
        await message.reply_text("🛑 Spamming rok di gayi hai.")
    else:
        await message.reply_text("⚠️ Spammer band hi hai.")

# ---------- Extra Security: Block All Other Users ----------
@bot.on_message(filters.command(["setgroup", "setmsg", "settime", "status", "start_spam", "stop_spam"]))
async def block_others(client, message):
    """Agar koi aur command use kare to block karo"""
    if message.from_user.id != OWNER_ID:
        await message.reply_text("🔒 You are not authorized to use this bot!")

# ---------- Flask Routes ----------
@server.route('/')
def home():
    return "Userbot Controller is running fine! 🚀", 200

@server.route('/health')
def health():
    return "OK", 200

# ---------- Main Function ----------
async def main():
    await bot.start()
    await user.start()
    print("🤖 Bot and 👤 User Client both started successfully!")
    print(f"🔐 Owner ID: {OWNER_ID}")
    print("📝 Logging enabled: command_logs.txt")
    
    asyncio.create_task(spam_worker())
    
    while True:
        await asyncio.sleep(1)

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    server.run(host='0.0.0.0', port=port, use_reloader=False, debug=False)

# ---------- Entry Point ----------
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
