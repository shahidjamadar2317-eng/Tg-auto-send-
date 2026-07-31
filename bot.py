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

# ---------- CONFIG: Multiple Groups ----------
spam_config = {
    "groups": [],  # 🔥 Multiple groups ki list
    "message": "Hello from Userbot! 🚀",
    "interval": 30,
    "is_running": False,
    "current_index": 0  # Current group index
}

# Clients
bot = Client("control_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user = Client("user_account", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# ---------- HELPERS ----------
def parse_group(group_input):
    """Convert username/ID/link to proper format"""
    group_input = group_input.strip()
    
    # Agar link hai (t.me/)
    if "t.me/" in group_input:
        group_input = group_input.split("t.me/")[1]
    
    # Agar username hai toh @ lagao
    if not group_input.startswith("@") and not group_input.startswith("-"):
        group_input = f"@{group_input}"
    
    return group_input

# ---------- SPAM WORKER ----------
async def spam_worker():
    while True:
        if spam_config["is_running"] and spam_config["groups"]:
            try:
                # Har group mein ek ek karke message bhejo
                for group in spam_config["groups"]:
                    try:
                        await user.send_message(group, spam_config["message"])
                        print(f"[+] Message sent to {group}")
                    except Exception as e:
                        print(f"[-] Error sending to {group}: {e}")
                    
                    # Har group ke baad thoda wait
                    await asyncio.sleep(5)
                
                # Sab groups mein bhejne ke baad interval wait
                await asyncio.sleep(spam_config["interval"])
                
            except Exception as e:
                print(f"[-] Spam Error: {e}")
                await asyncio.sleep(10)
        else:
            await asyncio.sleep(1)

# ---------- BOT COMMANDS ----------
@bot.on_message(filters.command(["start", "help"]))
async def start_command(client, message):
    help_text = (
        "🤖 **Userbot Controller**\n\n"
        "📌 **Group Commands:**\n"
        "/addgroup @username or -100xxxx - Add group\n"
        "/addgroup id:-100xxxx - Add by ID\n"
        "/removegroup @username - Remove group\n"
        "/listgroups - Show all groups\n"
        "/cleargroups - Remove all groups\n\n"
        "📌 **Spam Commands:**\n"
        "/setmsg Your text - Set message\n"
        "/settime 30 - Set interval (min 10s)\n"
        "/start_spam - Start spamming\n"
        "/stop_spam - Stop spamming\n"
        "/status - Check config\n\n"
        "🔓 Open for everyone!"
    )
    await message.reply_text(help_text)

@bot.on_message(filters.command("addgroup"))
async def add_group(client, message):
    try:
        group_input = message.text.split(maxsplit=1)[1]
        group = parse_group(group_input)
        
        if group in spam_config["groups"]:
            await message.reply_text(f"⚠️ Group already added: `{group}`")
            return
        
        spam_config["groups"].append(group)
        await message.reply_text(f"✅ Group added: `{group}`\n📊 Total groups: {len(spam_config['groups'])}")
    except:
        await message.reply_text("❌ Format: `/addgroup @username` or `/addgroup -100123456789`")

@bot.on_message(filters.command("removegroup"))
async def remove_group(client, message):
    try:
        group_input = message.text.split(maxsplit=1)[1]
        group = parse_group(group_input)
        
        if group not in spam_config["groups"]:
            await message.reply_text(f"❌ Group not found: `{group}`")
            return
        
        spam_config["groups"].remove(group)
        await message.reply_text(f"✅ Group removed: `{group}`\n📊 Total groups: {len(spam_config['groups'])}")
    except:
        await message.reply_text("❌ Format: `/removegroup @username`")

@bot.on_message(filters.command("listgroups"))
async def list_groups(client, message):
    if not spam_config["groups"]:
        await message.reply_text("📭 No groups added yet!\nUse `/addgroup @username` to add.")
        return
    
    groups_list = "\n".join([f"• {i+1}. `{g}`" for i, g in enumerate(spam_config["groups"])])
    await message.reply_text(
        f"📋 **Added Groups ({len(spam_config['groups'])}):**\n\n{groups_list}"
    )

@bot.on_message(filters.command("cleargroups"))
async def clear_groups(client, message):
    if not spam_config["groups"]:
        await message.reply_text("📭 No groups to clear!")
        return
    
    count = len(spam_config["groups"])
    spam_config["groups"] = []
    await message.reply_text(f"🗑️ Removed all {count} groups!")

@bot.on_message(filters.command("setmsg"))
async def set_msg(client, message):
    try:
        msg = message.text.split(maxsplit=1)[1]
        spam_config["message"] = msg
        await message.reply_text(f"✅ Message set:\n`{msg}`")
    except:
        await message.reply_text("❌ Format: `/setmsg Your text here`")

@bot.on_message(filters.command("settime"))
async def set_time(client, message):
    try:
        sec = int(message.text.split(maxsplit=1)[1])
        if sec < 10:
            await message.reply_text("⚠️ Minimum 10 seconds required!")
            return
        spam_config["interval"] = sec
        await message.reply_text(f"✅ Interval set: {sec} seconds")
    except:
        await message.reply_text("❌ Format: `/settime 30`")

@bot.on_message(filters.command("status"))
async def status(client, message):
    status_text = (
        f"📊 **Current Status**\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Groups: `{len(spam_config['groups'])}`\n"
        f"Message: `{spam_config['message']}`\n"
        f"Interval: `{spam_config['interval']}s`\n"
        f"Running: `{'✅ YES' if spam_config['is_running'] else '❌ NO'}`\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Use `/listgroups` to see all groups"
    )
    await message.reply_text(status_text)

@bot.on_message(filters.command("start_spam"))
async def start_spam(client, message):
    if not spam_config["groups"]:
        await message.reply_text("❌ Add at least one group using `/addgroup`")
        return
    
    if not spam_config["is_running"]:
        spam_config["is_running"] = True
        await message.reply_text(
            f"🚀 **Spamming started!**\n"
            f"📊 Groups: {len(spam_config['groups'])}\n"
            f"⏱️ Interval: {spam_config['interval']}s\n"
            f"💬 Message: `{spam_config['message']}`"
        )
    else:
        await message.reply_text("⚠️ Spam already running!")

@bot.on_message(filters.command("stop_spam"))
async def stop_spam(client, message):
    if spam_config["is_running"]:
        spam_config["is_running"] = False
        await message.reply_text("🛑 **Spamming stopped!**")
    else:
        await message.reply_text("⚠️ Spam is not running!")

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
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        loop.run_until_complete(main())
    except Exception as e:
        print(f"Error: {e}")
