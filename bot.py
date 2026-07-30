import asyncio
import os
import threading
import time
from datetime import datetime
from collections import defaultdict
from flask import Flask
from pyrogram import Client, filters

# ---------- ENVIRONMENT VARIABLES ----------
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# ---------- RATE LIMITING ----------
user_last_command = defaultdict(float)

def rate_limit(user_id, cooldown=3):
    current_time = time.time()
    if current_time - user_last_command[user_id] < cooldown:
        return False
    user_last_command[user_id] = current_time
    return True

# ---------- FLASK APP ----------
server = Flask(__name__)

# ---------- CONFIG ----------
spam_config = {
    "chat_id": None,
    "message": "Hello from Userbot! 🚀",
    "interval": 30,
    "is_running": False
}

# ---------- CLIENTS ----------
bot = Client("control_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client("user_account", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ---------- LOGGER ----------
def log_command(user_id, command):
    try:
        with open("command_logs.txt", "a") as f:
            f.write(f"{datetime.now()} | User: {user_id} | Command: {command}\n")
    except:
        pass

# ---------- SPAM WORKER ----------
async def spam_worker():
    while True:
        if spam_config["is_running"] and spam_config["chat_id"]:
            try:
                await user.send_message(spam_config["chat_id"], spam_config["message"])
                print(f"[+] Message sent to {spam_config['chat_id']}")
            except Exception as e:
                print(f"[-] Error: {e}")
            await asyncio.sleep(spam_config["interval"])
        else:
            await asyncio.sleep(1)

# ---------- OWNER ONLY DECORATOR ----------
def owner_only(func):
    async def wrapper(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("❌ Unauthorized!")
            return
        if message.chat.type != "private":
            await message.reply("❌ Private chat only!")
            return
        if not rate_limit(message.from_user.id):
            await message.reply("⏳ Slow down! Wait 3 seconds.")
            return
        log_command(message.from_user.id, message.text)
        return await func(client, message)
    return wrapper

# ---------- BOT COMMANDS ----------
@bot.on_message(filters.command(["start", "help"]))
@owner_only
async def start_command(client, message):
    help_text = (
        "🤖 USERBOT CONTROLLER\n"
        "━━━━━━━━━━━━━━━━\n"
        "/setgroup @username - Target group\n"
        "/setmsg Your text - Message set\n"
        "/settime 30 - Interval (min 10s)\n"
        "/status - Check config\n"
        "/start_spam - Start spamming\n"
        "/stop_spam - Stop spamming\n"
        "━━━━━━━━━━━━━━━━\n"
        "🔐 Only owner can use this bot!"
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
        await message.reply_text(f"✅ Target group set: `{group}`")
    except:
        await message.reply_text("❌ Format: /setgroup @username")

@bot.on_message(filters.command("setmsg"))
@owner_only
async def set_msg(client, message):
    try:
        msg = message.text.split(maxsplit=1)[1]
        spam_config["message"] = msg
        await message.reply_text(f"✅ Message set:\n`{msg}`")
    except:
        await message.reply_text("❌ Format: /setmsg Your text here")

@bot.on_message(filters.command("settime"))
@owner_only
async def set_time(client, message):
    try:
        sec = int(message.text.split(maxsplit=1)[1])
        if sec < 10:
            await message.reply_text("⚠️ Minimum 10 seconds required!")
            return
        spam_config["interval"] = sec
        await message.reply_text(f"✅ Interval set: {sec} seconds")
    except:
        await message.reply_text("❌ Format: /settime 30")

@bot.on_message(filters.command("status"))
@owner_only
async def status(client, message):
    status_text = (
        f"📊 CURRENT STATUS\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Target Chat: `{spam_config['chat_id']}`\n"
        f"Message: `{spam_config['message']}`\n"
        f"Interval: `{spam_config['interval']}s`\n"
        f"Running: `{'✅ YES' if spam_config['is_running'] else '❌ NO'}`\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Owner ID: `{OWNER_ID}`"
    )
    await message.reply_text(status_text)

@bot.on_message(filters.command("start_spam"))
@owner_only
async def start_spam(client, message):
    if not spam_config["chat_id"]:
        await message.reply_text("❌ First set group using /setgroup")
        return
    if not spam_config["is_running"]:
        spam_config["is_running"] = True
        await message.reply_text("🚀 Spamming started successfully!")
    else:
        await message.reply_text("⚠️ Spam already running!")

@bot.on_message(filters.command("stop_spam"))
@owner_only
async def stop_spam(client, message):
    if spam_config["is_running"]:
        spam_config["is_running"] = False
        await message.reply_text("🛑 Spamming stopped!")
    else:
        await message.reply_text("⚠️ Spam is not running!")

# ---------- BLOCK OTHERS ----------
@bot.on_message(filters.command(["setgroup", "setmsg", "settime", "status", "start_spam", "stop_spam"]))
async def block_others(client, message):
    if message.from_user.id != OWNER_ID:
        await message.reply_text("🔒 You are not authorized to use this bot!")

# ---------- FLASK ROUTES ----------
@server.route('/')
def home():
    return "Userbot is running! 🚀", 200

@server.route('/health')
def health():
    return "OK", 200

# ---------- MAIN ----------
async def main():
    await bot.start()
    await user.start()
    print("✅ Bot and User client started successfully!")
    print(f"🔐 Owner ID: {OWNER_ID}")
    print("📝 Logging enabled: command_logs.txt")
    
    asyncio.create_task(spam_worker())
    
    while True:
        await asyncio.sleep(1)

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    server.run(host='0.0.0.0', port=port, use_reloader=False, debug=False)

# ---------- ENTRY POINT ----------
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
