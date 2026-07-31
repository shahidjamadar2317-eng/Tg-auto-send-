import asyncio
import os
import threading
import sys
import re
from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, UserNotParticipant

# 🔥 Telethon support ke liye
from telethon import TelegramClient
from telethon.errors import FloodWaitError

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

# 🔥 Pyrogram Sessions
PYROGRAM_SESSIONS = os.getenv("PYROGRAM_SESSIONS", "").split(',')

# 🔥 Telethon Sessions
TELETHON_SESSIONS = os.getenv("TELETHON_SESSIONS", "").split(',')

# Flask app
server = Flask(__name__)

# ---------- CONFIG ----------
spam_config = {
    "groups": [],
    "message": "Hello from Userbot! 🚀",
    "interval": 30,
    "is_running": False
}

# ---------- CLIENTS ----------
# Bot (Pyrogram)
bot = Client("control_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# 🔥 Pyrogram User Clients
pyro_clients = []
for i, session in enumerate(PYROGRAM_SESSIONS):
    session = session.strip()
    if session:
        pyro_clients.append({
            "type": "pyrogram",
            "client": Client(f"pyro_{i}", api_id=API_ID, api_hash=API_HASH, session_string=session)
        })

# 🔥 Telethon User Clients
tele_clients = []
for i, session in enumerate(TELETHON_SESSIONS):
    session = session.strip()
    if session:
        tele_clients.append({
            "type": "telethon",
            "client": TelegramClient(session, API_ID, API_HASH)
        })

# ---------- HELPERS ----------
def parse_group(group_input):
    group_input = group_input.strip()
    if "t.me/" in group_input:
        if "joinchat" in group_input:
            group_input = group_input.split("t.me/joinchat/")[1]
        else:
            group_input = group_input.split("t.me/")[1]
    if not group_input.startswith("@") and not group_input.startswith("-"):
        group_input = f"@{group_input}"
    return group_input

async def send_message_pyrogram(client, group, message):
    try:
        await client.send_message(group, message)
        return True
    except Exception as e:
        print(f"[-] Pyrogram Error: {e}")
        return False

async def send_message_telethon(client, group, message):
    try:
        await client.send_message(group, message)
        return True
    except Exception as e:
        print(f"[-] Telethon Error: {e}")
        return False

# ---------- SPAM WORKER ----------
async def spam_worker():
    while True:
        if spam_config["is_running"] and spam_config["groups"]:
            for group in spam_config["groups"]:
                # 🔥 Pyrogram clients
                for item in pyro_clients:
                    try:
                        await send_message_pyrogram(item["client"], group, spam_config["message"])
                        print(f"[+] Pyrogram: Message sent to {group}")
                    except FloodWait as e:
                        wait = e.value + 10
                        print(f"[!] Pyrogram Flood wait! {wait}s")
                        await asyncio.sleep(wait)
                    except Exception as e:
                        print(f"[-] Pyrogram Error: {e}")
                    await asyncio.sleep(2)
                
                # 🔥 Telethon clients
                for item in tele_clients:
                    try:
                        await send_message_telethon(item["client"], group, spam_config["message"])
                        print(f"[+] Telethon: Message sent to {group}")
                    except FloodWaitError as e:
                        wait = e.seconds + 10
                        print(f"[!] Telethon Flood wait! {wait}s")
                        await asyncio.sleep(wait)
                    except Exception as e:
                        print(f"[-] Telethon Error: {e}")
                    await asyncio.sleep(2)
                
                await asyncio.sleep(3)
            
            await asyncio.sleep(spam_config["interval"])
        else:
            await asyncio.sleep(1)

# ---------- BOT COMMANDS ----------
@bot.on_message(filters.command(["start", "help"]))
async def start_command(client, message):
    total_accounts = len(pyro_clients) + len(tele_clients)
    help_text = (
        "🤖 **Userbot Controller**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Pyrogram: `{len(pyro_clients)}`\n"
        f"👤 Telethon: `{len(tele_clients)}`\n"
        f"📊 Groups: `{len(spam_config['groups'])}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📌 **Group Commands:**\n"
        "/addgroup @username - Add by username\n"
        "/addgroup -100xxxx - Add by ID\n"
        "/addgroup t.me/group - Add by link\n"
        "/removegroup @username - Remove group\n"
        "/listgroups - Show all groups\n"
        "/cleargroups - Remove all groups\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📌 **Spam Commands:**\n"
        "/setmsg Your text - Set message\n"
        "/settime 30 - Set interval (min 10s)\n"
        "/start_spam - Start spamming\n"
        "/stop_spam - Stop spamming\n"
        "/status - Check config"
    )
    await message.reply_text(help_text)

@bot.on_message(filters.command("addgroup"))
async def add_group(client, message):
    try:
        group_input = message.text.split(maxsplit=1)[1]
        group = parse_group(group_input)
        
        if group in spam_config["groups"]:
            await message.reply_text(f"⚠️ Already added: `{group}`")
            return
        
        spam_config["groups"].append(group)
        await message.reply_text(
            f"✅ **Group Added!**\n"
            f"📌 `{group}`\n"
            f"📊 Total: `{len(spam_config['groups'])}`"
        )
    except:
        await message.reply_text(
            "❌ **Format:**\n"
            "/addgroup @username\n"
            "/addgroup -100123456789\n"
            "/addgroup t.me/groupname"
        )

@bot.on_message(filters.command("removegroup"))
async def remove_group(client, message):
    try:
        group_input = message.text.split(maxsplit=1)[1]
        group = parse_group(group_input)
        
        if group not in spam_config["groups"]:
            await message.reply_text(f"❌ Not found: `{group}`")
            return
        
        spam_config["groups"].remove(group)
        await message.reply_text(f"✅ Removed: `{group}`\n📊 Total: `{len(spam_config['groups'])}`")
    except:
        await message.reply_text("❌ /removegroup @username")

@bot.on_message(filters.command("listgroups"))
async def list_groups(client, message):
    if not spam_config["groups"]:
        await message.reply_text("📭 **No groups added!**")
        return
    
    groups_list = "\n".join([f"• {i+1}. `{g}`" for i, g in enumerate(spam_config["groups"])])
    await message.reply_text(f"📋 **Groups ({len(spam_config['groups'])}):**\n\n{groups_list}")

@bot.on_message(filters.command("cleargroups"))
async def clear_groups(client, message):
    count = len(spam_config["groups"])
    spam_config["groups"] = []
    await message.reply_text(f"🗑️ **Removed all {count} groups!**")

@bot.on_message(filters.command("setmsg"))
async def set_msg(client, message):
    try:
        msg = message.text.split(maxsplit=1)[1]
        spam_config["message"] = msg
        await message.reply_text(f"✅ **Message set:**\n`{msg}`")
    except:
        await message.reply_text("❌ /setmsg Your text here")

@bot.on_message(filters.command("settime"))
async def set_time(client, message):
    try:
        sec = int(message.text.split(maxsplit=1)[1])
        if sec < 10:
            await message.reply_text("⚠️ Minimum 10 seconds required!")
            return
        spam_config["interval"] = sec
        await message.reply_text(f"✅ **Interval:** `{sec} seconds`")
    except:
        await message.reply_text("❌ /settime 30")

@bot.on_message(filters.command("status"))
async def status(client, message):
    total_accounts = len(pyro_clients) + len(tele_clients)
    status_text = (
        f"📊 **Current Status**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Pyrogram Accounts: `{len(pyro_clients)}`\n"
        f"Telethon Accounts: `{len(tele_clients)}`\n"
        f"Total Accounts: `{total_accounts}`\n"
        f"Groups: `{len(spam_config['groups'])}`\n"
        f"Message: `{spam_config['message']}`\n"
        f"Interval: `{spam_config['interval']}s`\n"
        f"Running: `{'✅ YES' if spam_config['is_running'] else '❌ NO'}`"
    )
    await message.reply_text(status_text)

@bot.on_message(filters.command("start_spam"))
async def start_spam(client, message):
    if not spam_config["groups"]:
        await message.reply_text("❌ **No groups!** Use `/addgroup @username`")
        return
    
    total_accounts = len(pyro_clients) + len(tele_clients)
    if total_accounts == 0:
        await message.reply_text("❌ **No accounts!** Add sessions in environment variables")
        return
    
    if not spam_config["is_running"]:
        spam_config["is_running"] = True
        await message.reply_text(
            f"🚀 **Spamming Started!**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Groups: `{len(spam_config['groups'])}`\n"
            f"👤 Total Accounts: `{total_accounts}`\n"
            f"⏱️ Interval: `{spam_config['interval']}s`\n"
            f"💬 Message: `{spam_config['message']}`"
        )
    else:
        await message.reply_text("⚠️ **Already running!**")

@bot.on_message(filters.command("stop_spam"))
async def stop_spam(client, message):
    if spam_config["is_running"]:
        spam_config["is_running"] = False
        await message.reply_text("🛑 **Spamming Stopped!**")
    else:
        await message.reply_text("⚠️ **Not running!**")

# ---------- FLASK ----------
@server.route('/')
def home():
    return "Userbot is running! 🚀", 200

# ---------- MAIN ----------
async def main():
    print("🤖 Starting bot...")
    await bot.start()
    print("✅ Bot started!")
    
    # 🔥 Start Pyrogram clients
    print("👤 Starting Pyrogram accounts...")
    for item in pyro_clients:
        try:
            await item["client"].start()
            print("✅ Pyrogram account started!")
        except Exception as e:
            print(f"❌ Pyrogram failed: {e}")
    
    # 🔥 Start Telethon clients
    print("👤 Starting Telethon accounts...")
    for item in tele_clients:
        try:
            await item["client"].start()
            print("✅ Telethon account started!")
        except Exception as e:
            print(f"❌ Telethon failed: {e}")
    
    total = len(pyro_clients) + len(tele_clients)
    print(f"📊 Total accounts: {total}")
    
    asyncio.create_task(spam_worker())
    
    while True:
        await asyncio.sleep(1)

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    server.run(host='0.0.0.0', port=port, use_reloader=False, debug=False)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        loop.run_until_complete(main())
    except Exception as e:
        print(f"❌ Error: {e}")
