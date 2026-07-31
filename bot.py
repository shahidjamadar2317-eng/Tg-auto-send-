import asyncio
import os
import threading
import sys
from flask import Flask
from pyrogram import Client, filters

# ---------- PYTHON 3.14 FIX ----------
if sys.version_info >= (3, 14):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
else:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# ---------- ENV VARIABLES ----------
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

# Flask app
server = Flask(__name__)

# Config
spam_config = {
    "chat_id": None,
    "message": "Hello from Userbot! 🚀",
    "interval": 30,
    "is_running": False
}

# Clients
bot = Client("control_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client("user_account", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

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

# ---------- BOT COMMANDS (No Owner Check) ----------
@bot.on_message(filters.command(["start", "help"]))
async def start_command(client, message):
    await message.reply_text(
        "🤖 **Userbot Controller**\n\n"
        "/setgroup @username - Set target group\n"
        "/setmsg Your text - Set message\n"
        "/settime 30 - Set interval (min 10s)\n"
        "/status - Check config\n"
        "/start_spam - Start spamming\n"
        "/stop_spam - Stop spamming\n\n"
        "🔓 Open for everyone!"
    )

@bot.on_message(filters.command("setgroup"))
async def set_group(client, message):
    try:
        group = message.text.split(maxsplit=1)[1]
        if "t.me/" in group:
            group = group.split("t.me/")[1]
        if not group.startswith("@"):
            group = f"@{group}"
        spam_config["chat_id"] = group
        await message.reply_text(f"✅ Target: `{group}`")
    except:
        await message.reply_text("❌ /setgroup @username")

@bot.on_message(filters.command("setmsg"))
async def set_msg(client, message):
    try:
        msg = message.text.split(maxsplit=1)[1]
        spam_config["message"] = msg
        await message.reply_text(f"✅ Message: `{msg}`")
    except:
        await message.reply_text("❌ /setmsg Your text")

@bot.on_message(filters.command("settime"))
async def set_time(client, message):
    try:
        sec = int(message.text.split(maxsplit=1)[1])
        if sec < 10:
            await message.reply_text("⚠️ Min 10 seconds")
            return
        spam_config["interval"] = sec
        await message.reply_text(f"✅ Interval: {sec}s")
    except:
        await message.reply_text("❌ /settime 30")

@bot.on_message(filters.command("status"))
async def status(client, message):
    await message.reply_text(
        f"📊 **Status**\n"
        f"Target: `{spam_config['chat_id']}`\n"
        f"Message: `{spam_config['message']}`\n"
        f"Interval: `{spam_config['interval']}s`\n"
        f"Running: `{'✅' if spam_config['is_running'] else '❌'}`"
    )

@bot.on_message(filters.command("start_spam"))
async def start_spam(client, message):
    if not spam_config["chat_id"]:
        await message.reply_text("❌ Set group first!")
        return
    if not spam_config["is_running"]:
        spam_config["is_running"] = True
        await message.reply_text("🚀 Spamming started!")
    else:
        await message.reply_text("⚠️ Already running!")

@bot.on_message(filters.command("stop_spam"))
async def stop_spam(client, message):
    if spam_config["is_running"]:
        spam_config["is_running"] = False
        await message.reply_text("🛑 Stopped!")
    else:
        await message.reply_text("⚠️ Not running!")

# ---------- FLASK ----------
@server.route('/')
def home():
    return "Userbot is running! 🚀", 200

# ---------- MAIN ----------
async def main():
    print("Starting bot...")
    await bot.start()
    print("✅ Bot started!")
    await user.start()
    print("✅ User client started!")
    
    asyncio.create_task(spam_worker())
    
    while True:
        await asyncio.sleep(1)

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    server.run(host='0.0.0.0', port=port, use_reloader=False, debug=False)

# ---------- ENTRY ----------
if __name__ == "__main__":
    # Flask thread
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Asyncio run
    try:
        loop.run_until_complete(main())
    except Exception as e:
        print(f"Error: {e}")
