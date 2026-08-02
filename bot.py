import os
import asyncio
import threading
import sys
from flask import Flask
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import Chat, Channel
from telethon import events

# ---------- CLEAR CACHE ----------
def clear_cache():
    try:
        for f in os.listdir('.'):
            if f.endswith('.session') or f.endswith('.session-journal'):
                os.remove(f)
    except:
        pass

clear_cache()
# ---------------------------------

if sys.version_info >= (3, 14):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
else:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# 🔥 Telethon Sessions (String sessions)
SESSION_STRINGS = os.getenv("SESSION_STRINGS", "").split(',')

server = Flask(__name__)

user_configs = {}

def get_config(user_id):
    if user_id not in user_configs:
        user_configs[user_id] = {
            "groups": [],
            "message": "Hello! 🚀",
            "interval": 30,
            "is_running": False,
            "selected_group": None
        }
    return user_configs[user_id]

# ---------- CLIENTS ----------
# Bot (Pyrogram - keep for commands)
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

bot = Client("control_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# 🔥 Telethon User Clients
user_clients = []
for i, s in enumerate(SESSION_STRINGS):
    s = s.strip()
    if s:
        user_clients.append({
            "name": f"Account_{i+1}",
            "client": TelegramClient(s, API_ID, API_HASH)
        })

# ---------- SPAM WORKER ----------
async def spam_worker():
    while True:
        for user_id, config in user_configs.items():
            if config["is_running"] and config["selected_group"] and user_clients:
                for user in user_clients:
                    try:
                        await user["client"].send_message(config["selected_group"], config["message"])
                        print(f"[+] {user['name']}: Message sent")
                    except FloodWaitError as e:
                        wait = e.seconds + 10
                        print(f"[!] Flood wait! {wait}s")
                        await asyncio.sleep(wait)
                    except Exception as e:
                        print(f"[-] Error: {e}")
                    await asyncio.sleep(2)
                await asyncio.sleep(config["interval"])
        await asyncio.sleep(1)

# ---------- COMMANDS ----------
@bot.on_message(filters.command(["start", "help"]))
async def start_cmd(client, message):
    await message.reply_text(
        "🤖 **Userbot Controller (Telethon)**\n"
        "/groups - Show joined groups\n"
        "/addgroup @username - Add group\n"
        "/listgroups - List added groups\n"
        "/cleargroups - Clear all\n"
        "/setmsg text - Set message\n"
        "/settime 30 - Set interval\n"
        "/start_spam - Start spamming\n"
        "/stop_spam - Stop spamming\n"
        "/status - Check status"
    )

@bot.on_message(filters.command("groups"))
async def groups_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    
    if not user_clients:
        await message.reply_text("❌ No accounts!")
        return
    
    try:
        groups = []
        async for dialog in user_clients[0]["client"].iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                groups.append({
                    "id": dialog.id,
                    "title": dialog.name,
                    "username": dialog.entity.username
                })
        
        if not groups:
            await message.reply_text("📭 No groups found!")
            return
        
        buttons = []
        for g in groups[:30]:
            name = g["title"][:25] if g["title"] else g["username"] or str(g["id"])
            buttons.append([InlineKeyboardButton(f"📌 {name}", callback_data=f"sel_{g['id']}")])
        
        await message.reply_text(
            f"📋 **Your Groups ({len(groups)})**\n"
            f"Selected: `{config['selected_group']}`",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)[:150]}")

@bot.on_callback_query()
async def callback(cq):
    user_id = cq.from_user.id
    config = get_config(user_id)
    
    if cq.data.startswith("sel_"):
        group_id = int(cq.data.split("_")[1])
        config["selected_group"] = group_id
        if group_id not in config["groups"]:
            config["groups"].append(group_id)
        await cq.answer("✅ Selected!")
        await cq.edit_message_text(f"✅ Selected: `{group_id}`\nUse /start_spam")

@bot.on_message(filters.command("addgroup"))
async def addgroup_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    try:
        g = message.text.split(maxsplit=1)[1].strip()
        if g in config["groups"]:
            await message.reply_text(f"⚠️ Already: `{g}`")
            return
        config["groups"].append(g)
        config["selected_group"] = g
        await message.reply_text(f"✅ Added: `{g}`")
    except:
        await message.reply_text("❌ /addgroup @username")

@bot.on_message(filters.command("listgroups"))
async def listgroups_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    if not config["groups"]:
        await message.reply_text("📭 No groups added!")
        return
    txt = "\n".join([f"• {i+1}. `{g}`" for i, g in enumerate(config["groups"])])
    await message.reply_text(f"📋 **Added Groups:**\n\n{txt}")

@bot.on_message(filters.command("cleargroups"))
async def cleargroups_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    count = len(config["groups"])
    config["groups"] = []
    config["selected_group"] = None
    await message.reply_text(f"🗑️ Removed {count} groups!")

@bot.on_message(filters.command("setmsg"))
async def setmsg_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    try:
        msg = message.text.split(maxsplit=1)[1]
        config["message"] = msg
        await message.reply_text(f"✅ Message: `{msg[:50]}...`")
    except:
        await message.reply_text("❌ /setmsg Your text")

@bot.on_message(filters.command("settime"))
async def settime_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    try:
        sec = int(message.text.split(maxsplit=1)[1])
        if sec < 10:
            await message.reply_text("⚠️ Min 10s")
            return
        config["interval"] = sec
        await message.reply_text(f"✅ Interval: `{sec}s`")
    except:
        await message.reply_text("❌ /settime 30")

@bot.on_message(filters.command("status"))
async def status_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    started = sum(1 for c in user_clients if c["client"].is_connected())
    await message.reply_text(
        f"📊 **Status (Telethon)**\n"
        f"Groups Added: `{len(config['groups'])}`\n"
        f"Selected: `{config['selected_group']}`\n"
        f"Message: `{config['message'][:30]}`\n"
        f"Interval: `{config['interval']}s`\n"
        f"Running: `{'✅' if config['is_running'] else '❌'}`\n"
        f"Accounts: `{started}/{len(user_clients)}`"
    )

@bot.on_message(filters.command("start_spam"))
async def start_spam_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    if not config["selected_group"]:
        await message.reply_text("❌ No group selected! Use /groups")
        return
    if not user_clients:
        await message.reply_text("❌ No accounts!")
        return
    if not config["is_running"]:
        config["is_running"] = True
        await message.reply_text(f"🚀 **Started!**\nGroup: `{config['selected_group']}`")
    else:
        await message.reply_text("⚠️ Already running!")

@bot.on_message(filters.command("stop_spam"))
async def stop_spam_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    if config["is_running"]:
        config["is_running"] = False
        await message.reply_text("🛑 Stopped!")
    else:
        await message.reply_text("⚠️ Not running!")

@server.route('/')
def home():
    return "Userbot running!", 200

async def main():
    print("🤖 Starting bot...")
    await bot.start()
    print("✅ Bot started!")
    
    print("👤 Starting Telethon accounts...")
    for user in user_clients:
        try:
            await user["client"].start()
            print(f"✅ {user['name']}: Started!")
        except Exception as e:
            print(f"❌ {user['name']}: Failed - {e}")
    
    print(f"📊 Total accounts: {len(user_clients)}")
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
