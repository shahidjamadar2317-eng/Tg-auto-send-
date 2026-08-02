import os
import shutil
import asyncio
import threading
import sys
from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------- 🔥 DATABASE CLEAR ----------
def clear_all_cache():
    try:
        for f in os.listdir('.'):
            if f.endswith('.session') or f.endswith('.session-journal'):
                os.remove(f)
                print(f"[+] Deleted: {f}")
        
        storage_path = '.venv/lib/python3.11/site-packages/pyrogram/storage/'
        if os.path.exists(storage_path):
            for f in os.listdir(storage_path):
                if f.endswith('.db') or f.endswith('.db-journal'):
                    os.remove(os.path.join(storage_path, f))
                    print(f"[+] Deleted storage: {f}")
        print("✅ Database cleared!")
    except Exception as e:
        print(f"[-] Clear error: {e}")

print("🗑️ Clearing database...")
clear_all_cache()
# ------------------------------------------------

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
SESSION_STRINGS = os.getenv("SESSION_STRINGS", "").split(',')

server = Flask(__name__)

user_configs = {}

def get_user_config(user_id):
    if user_id not in user_configs:
        user_configs[user_id] = {
            "groups": [],
            "message": "Hello from Userbot! 🚀",
            "interval": 30,
            "is_running": False,
            "selected_group": None
        }
    return user_configs[user_id]

bot = Client("control_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_clients = []
for i, session in enumerate(SESSION_STRINGS):
    session = session.strip()
    if session:
        user_clients.append({
            "name": f"Account_{i+1}",
            "client": Client(f"user_{i}", api_id=API_ID, api_hash=API_HASH, session_string=session)
        })

# ---------- BOT COMMANDS ----------
@bot.on_message(filters.command(["start", "help"]))
async def start_command(client, message):
    await message.reply_text(
        "🤖 **Userbot Controller**\n"
        "/groups - See joined groups\n"
        "/addgroup @username - Add group\n"
        "/listgroups - Show groups\n"
        "/cleargroups - Remove all\n"
        "/setmsg text - Set message\n"
        "/settime 30 - Set interval\n"
        "/start_spam - Start\n"
        "/stop_spam - Stop\n"
        "/status - Check status"
    )

@bot.on_message(filters.command("groups"))
async def show_groups(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    
    if not user_clients:
        await message.reply_text("❌ No accounts!")
        return
    
    try:
        # Check if connected
        if not user_clients[0]["client"].is_connected:
            await message.reply_text("⏳ Connecting, please wait 5 seconds!")
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
            await message.reply_text("📭 No groups found!")
            return
        
        buttons = []
        for group in groups[:50]:
            display_name = group["title"][:30] if group["title"] else group["username"] or str(group["id"])
            buttons.append([InlineKeyboardButton(f"📌 {display_name}", callback_data=f"select_{group['id']}")])
        
        await message.reply_text(
            f"📋 **Groups ({len(groups)})**\n"
            f"Click to select:\n"
            f"Selected: `{config['selected_group'] or 'None'}`",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)[:150]}")

@bot.on_callback_query()
async def callback_handler(client, callback_query):
    user_id = callback_query.from_user.id
    config = get_user_config(user_id)
    
    if callback_query.data.startswith("select_"):
        group_id = int(callback_query.data.split("_")[1])
        config["selected_group"] = group_id
        if group_id not in config["groups"]:
            config["groups"].append(group_id)
        
        await callback_query.answer("✅ Selected!")
        await callback_query.edit_message_text(f"✅ **Group Selected!**\nID: `{group_id}`\n\nUse `/start_spam`")

@bot.on_message(filters.command("addgroup"))
async def add_group(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    try:
        group = message.text.split(maxsplit=1)[1].strip()
        if group in config["groups"]:
            await message.reply_text(f"⚠️ Already added: `{group}`")
            return
        config["groups"].append(group)
        config["selected_group"] = group
        await message.reply_text(f"✅ Added: `{group}`")
    except:
        await message.reply_text("❌ /addgroup @username")

@bot.on_message(filters.command("listgroups"))
async def list_groups(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    if not config["groups"]:
        await message.reply_text("📭 No groups!")
        return
    groups_list = "\n".join([f"• {i+1}. `{g}`" for i, g in enumerate(config["groups"])])
    await message.reply_text(f"📋 **Groups:**\n\n{groups_list}")

@bot.on_message(filters.command("cleargroups"))
async def clear_groups(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    count = len(config["groups"])
    config["groups"] = []
    config["selected_group"] = None
    await message.reply_text(f"🗑️ Removed {count} groups!")

@bot.on_message(filters.command("setmsg"))
async def set_msg(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    try:
        msg = message.text.split(maxsplit=1)[1]
        config["message"] = msg
        await message.reply_text(f"✅ **Message:**\n`{msg}`")
    except:
        await message.reply_text("❌ /setmsg Your text")

@bot.on_message(filters.command("settime"))
async def set_time(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    try:
        sec = int(message.text.split(maxsplit=1)[1])
        if sec < 10:
            await message.reply_text("⚠️ Min 10 seconds!")
            return
        config["interval"] = sec
        await message.reply_text(f"✅ Interval: `{sec}s`")
    except:
        await message.reply_text("❌ /settime 30")

@bot.on_message(filters.command("status"))
async def status(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    
    accounts_started = 0
    for user in user_clients:
        if user["client"].is_connected:
            accounts_started += 1
    
    await message.reply_text(
        f"📊 **Status**\n"
        f"Groups: `{len(config['groups'])}`\n"
        f"Selected: `{config['selected_group'] or 'None'}`\n"
        f"Message: `{config['message']}`\n"
        f"Interval: `{config['interval']}s`\n"
        f"Running: `{'✅' if config['is_running'] else '❌'}`\n"
        f"Accounts: `{accounts_started}/{len(user_clients)}`"
    )

@bot.on_message(filters.command("start_spam"))
async def start_spam(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    
    if not config["selected_group"]:
        await message.reply_text("❌ No group selected! Use `/groups`")
        return
    
    if not user_clients:
        await message.reply_text("❌ No accounts!")
        return
    
    if not config["is_running"]:
        config["is_running"] = True
        await message.reply_text(
            f"🚀 **Started!**\n"
            f"Group: `{config['selected_group']}`\n"
            f"Accounts: `{len(user_clients)}`\n"
            f"Interval: `{config['interval']}s`"
        )
    else:
        await message.reply_text("⚠️ Already running!")

@bot.on_message(filters.command("stop_spam"))
async def stop_spam(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    if config["is_running"]:
        config["is_running"] = False
        await message.reply_text("🛑 Stopped!")
    else:
        await message.reply_text("⚠️ Not running!")

# ---------- SPAM WORKER ----------
async def spam_worker():
    while True:
        for user_id, config in user_configs.items():
            if config["is_running"] and config["selected_group"] and user_clients:
                group = config["selected_group"]
                for user in user_clients:
                    try:
                        await user["client"].send_message(group, config["message"])
                        print(f"[+] Message sent")
                    except FloodWait as e:
                        wait = e.value + 10
                        print(f"[!] Flood wait! {wait}s")
                        await asyncio.sleep(wait)
                    except Exception as e:
                        print(f"[-] Error: {e}")
                    await asyncio.sleep(2)
                await asyncio.sleep(config["interval"])
        await asyncio.sleep(1)

@server.route('/')
def home():
    return "Userbot running!", 200

async def main():
    print("🤖 Starting bot...")
    await bot.start()
    print("✅ Bot started!")
    
    print("👤 Starting accounts...")
    for user in user_clients:
        try:
            await user["client"].start()
            print(f"✅ {user['name']}: Started!")
        except Exception as e:
            print(f"❌ {user['name']}: Failed - {e}")
    
    print(f"📊 Total: {len(user_clients)}")
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
