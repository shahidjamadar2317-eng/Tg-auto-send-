import asyncio
import os
import threading
import sys
from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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

# 🔥 Per-user config
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

# ---------- SPAM WORKER ----------
async def spam_worker():
    while True:
        for user_id, config in user_configs.items():
            if config["is_running"] and config["selected_group"] and user_clients:
                group = config["selected_group"]
                for user in user_clients:
                    try:
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
                    except Exception as e:
                        print(f"[-] Error: {e}")
                    await asyncio.sleep(2)
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
        "/groups - See all joined groups\n"
        "/addgroup @username - Add by username\n"
        "/removegroup @username - Remove group\n"
        "/listgroups - Show added groups\n"
        "/cleargroups - Remove all groups\n"
        "/setmsg Your text - Set message\n"
        "/settime 30 - Set interval\n"
        "/start_spam - Start spamming\n"
        "/stop_spam - Stop spamming\n"
        "/status - Check config"
    )
    await message.reply_text(help_text)

# 🔥 NEW: Show all joined groups
@bot.on_message(filters.command("groups"))
async def show_groups(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    
    if not user_clients:
        await message.reply_text("❌ No accounts connected!")
        return
    
    try:
        # 🔥 Pehle account se groups fetch karo
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
        
        # 🔥 Buttons banao - har group ke liye
        buttons = []
        for group in groups[:50]:  # Max 50 groups
            display_name = group["title"][:30] if group["title"] else group["username"] or str(group["id"])
            callback_data = f"select_{group['id']}"
            buttons.append([InlineKeyboardButton(f"📌 {display_name}", callback_data=callback_data)])
        
        # Add to config buttons
        await message.reply_text(
            f"📋 **Your Groups ({len(groups)})**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Click on a group to select it for spamming!\n\n"
            f"Currently selected: `{config['selected_group'] or 'None'}`",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# 🔥 Callback handler for group selection
@bot.on_callback_query()
async def callback_handler(client, callback_query):
    user_id = callback_query.from_user.id
    config = get_user_config(user_id)
    
    if callback_query.data.startswith("select_"):
        group_id = int(callback_query.data.split("_")[1])
        
        # 🔥 Group select karo
        config["selected_group"] = group_id
        config["groups"].append(group_id) if group_id not in config["groups"] else None
        
        await callback_query.answer(f"✅ Group selected!")
        await callback_query.edit_message_text(
            f"✅ **Group Selected!**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Group ID: `{group_id}`\n\n"
            f"Now use `/start_spam` to start spamming!\n"
            f"Currently selected: `{group_id}`"
        )

# 🔥 Add group manually (username, ID, link)
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
        config["selected_group"] = group
        await message.reply_text(
            f"✅ **Group Added!**\n"
            f"📌 `{group}`\n"
            f"📊 Total: `{len(config['groups'])}`\n"
            f"Selected: `{group}`"
        )
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
        if config["selected_group"] == group:
            config["selected_group"] = None
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
    await message.reply_text(
        f"📋 **Your Groups ({len(config['groups'])}):**\n\n{groups_list}\n\n"
        f"Currently selected: `{config['selected_group'] or 'None'}`"
    )

@bot.on_message(filters.command("cleargroups"))
async def clear_groups(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    count = len(config["groups"])
    config["groups"] = []
    config["selected_group"] = None
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
        f"Selected Group: `{config['selected_group'] or 'None'}`\n"
        f"Message: `{config['message']}`\n"
        f"Interval: `{config['interval']}s`\n"
        f"Running: `{'✅ YES' if config['is_running'] else '❌ NO'}`\n"
        f"Accounts: `{len(user_clients)}`"
    )

@bot.on_message(filters.command("start_spam"))
async def start_spam(client, message):
    user_id = message.from_user.id
    config = get_user_config(user_id)
    
    if not config["selected_group"]:
        await message.reply_text("❌ **No group selected!**\nUse `/groups` to select a group.")
        return
    
    if not user_clients:
        await message.reply_text("❌ **No accounts!**")
        return
    
    if not config["is_running"]:
        config["is_running"] = True
        await message.reply_text(
            f"🚀 **Spamming Started!**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 Group: `{config['selected_group']}`\n"
            f"👤 Accounts: `{len(user_clients)}`\n"
            f"⏱️ Interval: `{config['interval']}s`\n"
            f"💬 Message: `{config['message']}`"
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
