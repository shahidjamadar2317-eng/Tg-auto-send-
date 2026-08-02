import asyncio
import os
import threading
import sys
import shutil
from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, UserNotParticipant

# ---------- 🔥 CACHE CLEAR ON START ----------
def clear_cache():
    try:
        for file in os.listdir('.'):
            if file.endswith('.session') or file.endswith('.session-journal'):
                os.remove(file)
                print(f"[+] Deleted: {file}")
        
        storage_path = '.venv/lib/python3.11/site-packages/pyrogram/storage/'
        if os.path.exists(storage_path):
            for file in os.listdir(storage_path):
                if file.endswith('.db') or file.endswith('.db-journal'):
                    os.remove(os.path.join(storage_path, file))
                    print(f"[+] Deleted storage: {file}")
    except Exception as e:
        print(f"[-] Cache clear error: {e}")

print("🗑️ Clearing cache...")
clear_cache()
print("✅ Cache cleared!")
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
            "is_running": False
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

async def spam_worker():
    while True:
        for user_id, config in user_configs.items():
            if config["is_running"] and config["groups"] and user_clients:
                for group in config["groups"]:
                    for user in user_clients:
                        try:
                            # 🔥 Force refresh
                            try:
                                await user["client"].get_chat(group)
                            except:
                                pass
                            
                            await user["client"].send_message(group, config["message"])
                            print(f"[+] {user['name']}: Message sent to {group}")
                        except FloodWait as e:
                            wait = e.value + 10
                            print(f"[!] Flood wait! {wait}s")
                            await asyncio.sleep(wait)
                        except UserNotParticipant:
                            print(f"[!] Not in group: {group}")
                            try:
                                await user["client"].join_chat(group)
                                print(f"[+] Joined: {group}")
                            except:
                                pass
                        except ValueError as e:
                            if "Peer id invalid" in str(e):
                                print(f"[!] Invalid peer, refreshing...")
                                try:
                                    await user["client"].get_chat(group)
                                except:
                                    pass
                        except Exception as e:
                            print(f"[-] Error: {e}")
                        await asyncio.sleep(2)
                    await asyncio.sleep(3)
                await asyncio.sleep(config["interval"])
        await asyncio.sleep(1)

# ---------- BOT COMMANDS ----------
@bot.on_message(filters.command(["start", "help"]))
async def start_command(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    help_text = (
        "🤖 **Userbot Controller**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Your ID: `{user_id}`\n"
        f"📊 Groups: `{len(config['groups'])}`\n"
        f"👤 Accounts: `{len(user_clients)}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "/addgroup @username - Add group\n"
        "/addgroup t.me/group - Add by link\n"
        "/removegroup @username - Remove group\n"
        "/listgroups - Show all groups\n"
        "/cleargroups - Remove all groups\n"
        "/setmsg Your text - Set message\n"
        "/settime 30 - Set interval\n"
        "/start_spam - Start spamming\n"
        "/stop_spam - Stop spamming\n"
        "/status - Check config"
    )
    await message.reply_text(help_text)

@bot.on_message(filters.command("addgroup"))
async def add_group(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    try:
        group_input = message.text.split(maxsplit=1)[1]
        group = parse_group(group_input)
        if group in config["groups"]:
            await message.reply_text(f"⚠️ Already added: `{group}`")
            return
        config["groups"].append(group)
        await message.reply_text(f"✅ **Group Added!**\n📌 `{group}`\n📊 Total: `{len(config['groups'])}`")
    except:
        await message.reply_text("❌ /addgroup @username or /addgroup t.me/group")

@bot.on_message(filters.command("removegroup"))
async def remove_group(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    try:
        group_input = message.text.split(maxsplit=1)[1]
        group = parse_group(group_input)
        if group not in config["groups"]:
            await message.reply_text(f"❌ Not found: `{group}`")
            return
        config["groups"].remove(group)
        await message.reply_text(f"✅ Removed: `{group}`\n📊 Total: `{len(config['groups'])}`")
    except:
        await message.reply_text("❌ /removegroup @username")

@bot.on_message(filters.command("listgroups"))
async def list_groups(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    if not config["groups"]:
        await message.reply_text("📭 **No groups added!**")
        return
    groups_list = "\n".join([f"• {i+1}. `{g}`" for i, g in enumerate(config["groups"])])
    await message.reply_text(f"📋 **Your Groups ({len(config['groups'])}):**\n\n{groups_list}")

@bot.on_message(filters.command("cleargroups"))
async def clear_groups(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    count = len(config["groups"])
    config["groups"] = []
    await message.reply_text(f"🗑️ **Removed all {count} groups!**")

@bot.on_message(filters.command("setmsg"))
async def set_msg(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    try:
        msg = message.text.split(maxsplit=1)[1]
        config["message"] = msg
        await message.reply_text(f"✅ **Message set:**\n`{msg}`")
    except:
        await message.reply_text("❌ /setmsg Your text here")

@bot.on_message(filters.command("settime"))
async def set_time(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    try:
        sec = int(message.text.split(maxsplit=1)[1])
        if sec < 10:
            await message.reply_text("⚠️ Minimum 10 seconds required!")
            return
        config["interval"] = sec
        await message.reply_text(f"✅ **Interval:** `{sec} seconds`")
    except:
        await message.reply_text("❌ /settime 30")

@bot.on_message(filters.command("status"))
async def status(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    await message.reply_text(
        f"📊 **Your Status**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"User ID: `{user_id}`\n"
        f"Groups: `{len(config['groups'])}`\n"
        f"Message: `{config['message']}`\n"
        f"Interval: `{config['interval']}s`\n"
        f"Running: `{'✅ YES' if config['is_running'] else '❌ NO'}`\n"
        f"Accounts: `{len(user_clients)}`"
    )

@bot.on_message(filters.command("start_spam"))
async def start_spam(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    if not config["groups"]:
        await message.reply_text("❌ **No groups!** Use `/addgroup`")
        return
    if not user_clients:
        await message.reply_text("❌ **No accounts!**")
        return
    if not config["is_running"]:
        config["is_running"] = True
        await message.reply_text(
            f"🚀 **Spamming Started!**\n"
            f"📊 Groups: `{len(config['groups'])}`\n"
            f"👤 Accounts: `{len(user_clients)}`\n"
            f"⏱️ Interval: `{config['interval']}s`"
        )
    else:
        await message.reply_text("⚠️ **Already running!**")

@bot.on_message(filters.command("stop_spam"))
async def stop_spam(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    if config["is_running"]:
        config["is_running"] = False
        await message.reply_text("🛑 **Spamming Stopped!**")
    else:
        await message.reply_text("⚠️ **Not running!**")

@server.route('/')
def home():
    return "Userbot is running! 🚀", 200

async def main():
    print("🤖 Starting bot...")
    await bot.start()
    print("✅ Bot started!")
    print("👤 Starting user accounts...")
    for user in user_clients:
        try:
            await user["client"].start()
            print(f"✅ {user['name']}: Started successfully!")
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
