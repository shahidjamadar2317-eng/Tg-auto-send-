import asyncio
import os
import threading
from flask import Flask
from pyrogram import Client, filters

# Environments variables (Render pe set karenge)
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))  # Sirf tum control kar sako

# Flask app to keep Render alive
server = Flask(__name__)

# Config stores
spam_config = {
    "chat_id": None,
    "message": "Hello from Userbot! 🚀",
    "interval": 30,
    "is_running": False
}

# Clients initialization
bot = Client("control_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client("user_account", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

async def spam_worker():
    """Background loop jo tumhare account se message bhejega"""
    while spam_config["is_running"]:
        if spam_config["chat_id"]:
            try:
                # 'user' client ka use karke tumhare account se message jayega
                await user.send_message(spam_config["chat_id"], spam_config["message"])
                print(f"[+] User account sent message to {spam_config['chat_id']}")
            except Exception as e:
                print(f"[-] Spam Error: {e}")
        await asyncio.sleep(spam_config["interval"])

@bot.on_message(filters.command(["start", "help"]) & filters.user(OWNER_ID))
async def start_command(client, message):
    help_text = (
        "🤖 **Userbot Controller Active!**\n\n"
        "Commands:\n"
        "/setgroup <ID/Username/Link> - Target group set karein\n"
        "/setmsg <text> - Prank text set karein\n"
        "/settime <seconds> - Time interval\n"
        "/status - Current configuration\n"
        "/start_spam - Account se spamming shuru karein\n"
        "/stop_spam - Spamming rokne ke liye"
    )
    await message.reply_text(help_text)

@bot.on_message(filters.command("setgroup") & filters.user(OWNER_ID))
async def set_group(client, message):
    try:
        group = message.text.split(maxsplit=1)[1]
        # Handle full links (e.g., t.me/groupname)
        if "t.me/" in group:
            group = group.split("t.me/")[1]
            if not group.startswith("@"):
                group = f"@{group}"
        
        spam_config["chat_id"] = group
        await message.reply_text(f"✅ Target Group Set: `{group}`")
    except IndexError:
        await message.reply_text("❌ Format: `/setgroup @groupusername` ya `/setgroup -100xxxxxxx`")

@bot.on_message(filters.command("setmsg") & filters.user(OWNER_ID))
async def set_msg(client, message):
    try:
        msg_text = message.text.split(maxsplit=1)[1]
        spam_config["message"] = msg_text
        await message.reply_text(f"✅ Message text set to:\n`{msg_text}`")
    except IndexError:
        await message.reply_text("❌ Format: `/setmsg Tera text yahan`")

@bot.on_message(filters.command("settime") & filters.user(OWNER_ID))
async def set_time(client, message):
    try:
        seconds = int(message.text.split(maxsplit=1)[1])
        if seconds < 10:
            await message.reply_text("⚠️ Account safety ke liye minimal 10 seconds rakhein.")
            return
        spam_config["interval"] = seconds
        await message.reply_text(f"✅ Interval Set: {seconds} seconds")
    except (IndexError, ValueError):
        await message.reply_text("❌ Format: `/settime 30`")

@bot.on_message(filters.command("status") & filters.user(OWNER_ID))
async def status(client, message):
    status_msg = (
        f"📊 **Current Status:**\n"
        f"Target Chat: `{spam_config['chat_id']}`\n"
        f"Message: `{spam_config['message']}`\n"
        f"Interval: `{spam_config['interval']}s`\n"
        f"Running: `{'YES' if spam_config['is_running'] else 'NO'}`"
    )
    await message.reply_text(status_msg)

@bot.on_message(filters.command("start_spam") & filters.user(OWNER_ID))
async def start_spam(client, message):
    if not spam_config["chat_id"]:
        await message.reply_text("❌ Pehle /setgroup set karo!")
        return
    
    if not spam_config["is_running"]:
        spam_config["is_running"] = True
        # Async background task loop shuru karein
        asyncio.create_task(spam_worker())
        await message.reply_text("🚀 Tumhare account se background spamming shuru ho chuki hai!")
    else:
        await message.reply_text("⚠️ Spammer pehle se hi chal raha hai.")

@bot.on_message(filters.command("stop_spam") & filters.user(OWNER_ID))
async def stop_spam(client, message):
    if spam_config["is_running"]:
        spam_config["is_running"] = False
        await message.reply_text("🛑 Spamming rok di gayi hai.")
    else:
        await message.reply_text("⚠️ Spammer band hi hai.")

@server.route('/')
def home():
    return "Userbot Controller is running fine!", 200

async def main():
    # Dono clients ko parallel me start karenge
    await bot.start()
    await user.start()
    print("🤖 Bot and 👤 User Client both started successfully!")
    
    # Loop running rakhne ke liye
    await asyncio.Event().wait()

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    server.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # Flask ko separate thread me run karenge taaki Render port active rahe
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Main Asyncio loop chalao Pyrogram ke liye
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
