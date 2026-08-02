import os
import asyncio
import threading
import sys
import time
from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------- CLEAR CACHE ----------
def clear_cache():
    try:
        for f in os.listdir('.'):
            if f.endswith('.session') or f.endswith('.session-journal'):
                os.remove(f)
                print(f"[+] Deleted: {f}")
    except:
        pass

print("🗑️ Clearing cache...")
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

# ---------- ENV VARIABLES ----------
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRINGS = os.getenv("SESSION_STRINGS", "").split(',')

server = Flask(__name__)

# ---------- CONFIG ----------
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
# Bot
bot = Client("control_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# 🔥 Pyrogram User Clients
user_clients = []
for i, s in enumerate(SESSION_STRINGS):
    s = s.strip()
    if s:
        try:
            client = Client(f"user_{i}", api_id=API_ID, api_hash=API_HASH, session_string=s)
            user_clients.append({
                "name": f"Account_{i+1}",
                "client": client
            })
            print(f"✅ Account_{i+1} initialized")
        except Exception as e:
            print(f"❌ Account_{i+1} init error: {e}")

# ---------- SPAM WORKER ----------
async def spam_worker():
    while True:
        try:
            for user_id, config in user_configs.items():
                if config["is_running"] and config["selected_group"] and user_clients:
                    for user in user_clients:
                        try:
                            await user["client"].send_message(config["selected_group"], config["message"])
                            print(f"[+] {user['name']}: Message sent to {config['selected_group']}")
                        except FloodWait as e:
                            wait = e.value + 10
                            print(f"[!] Flood wait! {wait}s")
                            await asyncio.sleep(wait)
                        except UserNotParticipant:
                            print(f"[!] Not in group, trying to join...")
                            try:
                                await user["client"].join_chat(config["selected_group"])
                                print(f"[+] Joined group!")
                            except Exception as e:
                                print(f"[-] Cannot join: {e}")
                        except Exception as e:
                            print(f"[-] Error: {e}")
                        await asyncio.sleep(2)
                    await asyncio.sleep(config["interval"])
        except Exception as e:
            print(f"[-] Spam worker error: {e}")
        await asyncio.sleep(1)

# ---------- KEEP ALIVE ----------
def keep_alive():
    try:
        import requests
        url = os.getenv("RENDER_EXTERNAL_URL", "https://tg-auto-send-1.onrender.com")
        while True:
            try:
                requests.get(url)
                print("[+] Keep alive ping sent")
            except:
                pass
            time.sleep(300)
    except:
        pass

# ---------- BOT COMMANDS ----------
@bot.on_message(filters.command(["start", "help"]))
async def start_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    await message.reply_text(
        f"🤖 **Userbot Controller**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 User ID: `{user_id}`\n"
        f"📊 Groups: `{len(config['groups'])}`\n"
        f"👤 Accounts: `{len(user_clients)}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        "📌 **Commands:**\n"
        "/groups - Show joined groups\n"
        "/addgroup @username - Add group\n"
        "/listgroups - List added groups\n"
        "/cleargroups - Clear all groups\n"
        "/setmsg text - Set message\n"
        "/settime 30 - Set interval (min 10s)\n"
        "/start_spam - Start spamming\n"
        "/stop_spam - Stop spamming\n"
        "/status - Check status"
    )

@bot.on_message(filters.command("groups"))
async def groups_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    
    if not user_clients:
        await message.reply_text("❌ No accounts connected!\nCheck SESSION_STRINGS.")
        return
    
    try:
        if not user_clients[0]["client"].is_connected:
            await message.reply_text("⏳ Connecting... Please wait 5 seconds!")
            return
        
        groups = []
        async for dialog in user_clients[0]["client"].get_dialogs():
            if dialog.chat.type in ["group", "supergroup", "channel"]:
                groups.append({
                    "id": dialog.chat.id,
                    "title": dialog.chat.title,
                    "username": dialog.chat.username
                })
        
        if not groups:
            await message.reply_text("📭 No groups found!\nMake sure accounts are joined to groups.")
            return
        
        buttons = []
        for g in groups[:30]:
            name = g["title"][:25] if g["title"] else g["username"] or str(g["id"])
            buttons.append([InlineKeyboardButton(f"📌 {name}", callback_data=f"sel_{g['id']}")])
        
        await message.reply_text(
            f"📋 **Your Groups ({len(groups)})**\n"
            f"Click to select a group:\n"
            f"Selected: `{config['selected_group'] or 'None'}`",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)[:150]}")

@bot.on_callback_query()
async def callback(cq):
    user_id = cq.from_user.id
    config = get_config(user_id)
    
    if cq.data.startswith("sel_"):
        try:
            group_id = int(cq.data.split("_")[1])
            config["selected_group"] = group_id
            if group_id not in config["groups"]:
                config["groups"].append(group_id)
            await cq.answer("✅ Group Selected!")
            await cq.edit_message_text(
                f"✅ **Group Selected!**\n"
                f"ID: `{group_id}`\n\n"
                f"Use `/start_spam` to start spamming!"
            )
        except Exception as e:
            await cq.answer(f"❌ Error")

@bot.on_message(filters.command("addgroup"))
async def addgroup_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    try:
        g = message.text.split(maxsplit=1)[1].strip()
        if g in config["groups"]:
            await message.reply_text(f"⚠️ Already added: `{g}`")
            return
        config["groups"].append(g)
        config["selected_group"] = g
        await message.reply_text(f"✅ **Group Added!**\n📌 `{g}`")
    except:
        await message.reply_text("❌ /addgroup @username or /addgroup t.me/group")

@bot.on_message(filters.command("listgroups"))
async def listgroups_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    if not config["groups"]:
        await message.reply_text("📭 No groups added!")
        return
    txt = "\n".join([f"• {i+1}. `{g}`" for i, g in enumerate(config["groups"])])
    await message.reply_text(f"📋 **Your Groups ({len(config['groups'])}):**\n\n{txt}")

@bot.on_message(filters.command("cleargroups"))
async def cleargroups_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    count = len(config["groups"])
    config["groups"] = []
    config["selected_group"] = None
    await message.reply_text(f"🗑️ Removed all {count} groups!")

@bot.on_message(filters.command("setmsg"))
async def setmsg_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    try:
        msg = message.text.split(maxsplit=1)[1]
        config["message"] = msg
        await message.reply_text(f"✅ **Message set:**\n`{msg}`")
    except:
        await message.reply_text("❌ /setmsg Your text here")

@bot.on_message(filters.command("settime"))
async def settime_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    try:
        sec = int(message.text.split(maxsplit=1)[1])
        if sec < 10:
            await message.reply_text("⚠️ Minimum 10 seconds required!")
            return
        config["interval"] = sec
        await message.reply_text(f"✅ **Interval set:** `{sec} seconds`")
    except:
        await message.reply_text("❌ /settime 30")

@bot.on_message(filters.command("status"))
async def status_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    
    connected = 0
    for c in user_clients:
        try:
            if c["client"].is_connected:
                connected += 1
        except:
            pass
    
    status_text = (
        f"📊 **Status**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"User ID: `{user_id}`\n"
        f"Groups Added: `{len(config['groups'])}`\n"
        f"Selected Group: `{config['selected_group'] or 'None'}`\n"
        f"Message: `{config['message'][:30]}{'...' if len(config['message']) > 30 else ''}`\n"
        f"Interval: `{config['interval']}s`\n"
        f"Running: `{'✅ YES' if config['is_running'] else '❌ NO'}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Accounts Connected: `{connected}/{len(user_clients)}`"
    )
    
    if connected == 0:
        status_text += "\n\n⚠️ **No accounts connected!**\nCheck SESSION_STRINGS in environment variables."
    
    await message.reply_text(status_text)

@bot.on_message(filters.command("start_spam"))
async def start_spam_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    
    if not config["selected_group"]:
        await message.reply_text("❌ **No group selected!**\nUse `/groups` to select a group.")
        return
    
    if not user_clients:
        await message.reply_text("❌ **No accounts!**\nCheck SESSION_STRINGS.")
        return
    
    if not config["is_running"]:
        config["is_running"] = True
        await message.reply_text(
            f"🚀 **Spamming Started!**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 Group: `{config['selected_group']}`\n"
            f"👤 Accounts: `{len(user_clients)}`\n"
            f"⏱️ Interval: `{config['interval']}s`\n"
            f"💬 Message: `{config['message'][:50]}{'...' if len(config['message']) > 50 else ''}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🛑 Use `/stop_spam` to stop"
        )
    else:
        await message.reply_text("⚠️ **Already running!**")

@bot.on_message(filters.command("stop_spam"))
async def stop_spam_cmd(client, message):
    user_id = message.from_user.id
    config = get_config(user_id)
    if config["is_running"]:
        config["is_running"] = False
        await message.reply_text("🛑 **Spamming Stopped!**")
    else:
        await message.reply_text("⚠️ **Not running!**")

@server.route('/')
def home():
    return "Userbot is running! 🚀", 200

# ---------- MAIN ----------
async def main():
    print("=" * 40)
    print("🤖 STARTING USERBOT CONTROLLER")
    print("=" * 40)
    
    print("\n📱 Starting bot...")
    await bot.start()
    print("✅ Bot started successfully!")
    
    print("\n👤 Starting user accounts...")
    for user in user_clients:
        try:
            await user["client"].start()
            print(f"✅ {user['name']}: Started successfully!")
        except Exception as e:
            print(f"❌ {user['name']}: Failed - {e}")
    
    print(f"\n📊 Total accounts: {len(user_clients)}")
    print("=" * 40)
    print("✅ USERBOT IS READY!")
    print("=" * 40)
    
    asyncio.create_task(spam_worker())
    
    while True:
        await asyncio.sleep(1)

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    server.run(host='0.0.0.0', port=port, use_reloader=False, debug=False)

# ---------- ENTRY POINT ----------
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    
    try:
        import requests
        threading.Thread(target=keep_alive, daemon=True).start()
    except:
        pass
    
    try:
        loop.run_until_complete(main())
    except Exception as e:
        print(f"❌ Error: {e}")
        print("🔄 Restarting in 10 seconds...")
        time.sleep(10)
        os.execv(sys.executable, ['python'] + sys.argv)
