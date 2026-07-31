from pyrogram import Client, filters
from pyrogram.errors import FloodWait
import asyncio
import time
import threading
from flask import Flask
import requests
import logging

# ============ CONFIGURATION ============
API_ID = 123456  # Apna API ID daalein
API_HASH = "your_api_hash_here"  # Apna API Hash
BOT_TOKEN = "your_bot_token_here"  # Apna Bot Token

# Telegram bot initialize
app_bot = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Flask app for keep-alive
flask_app = Flask(__name__)

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ KEEP-ALIVE FLASK SERVER ============
@flask_app.route('/')
def home():
    return "✅ Bot is Alive & Running!", 200

@flask_app.route('/ping')
def ping():
    return "Pong!", 200

def run_flask():
    """Flask server chalayein background mein"""
    flask_app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

# ============ SELF-PING FUNCTION ============
def self_ping():
    """Har 5 minute mein apne aap ko ping karein"""
    while True:
        time.sleep(300)  # 5 minutes
        try:
            # Render par deploy hai toh ye URL use karein
            # Local testing ke liye localhost
            response = requests.get('http://localhost:8080/ping', timeout=5)
            logger.info(f"✅ Self-ping successful: {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ Self-ping failed: {e}")

# ============ FLOOD WAIT HANDLER ============
async def safe_send_message(chat_id, text):
    """Flood wait handle karne ke liye wrapper function"""
    try:
        await app_bot.send_message(chat_id, text)
        return True
    except FloodWait as e:
        wait_time = e.value
        logger.warning(f"⏳ Flood wait: {wait_time} seconds")
        
        # Agar wait time zyada hai toh notify karein
        if wait_time > 60:
            logger.error(f"❌ Long flood wait: {wait_time}s - Bot might be blocked")
            # Admin ko notify karein (optional)
            await app_bot.send_message(YOUR_ADMIN_ID, f"⚠️ Flood wait: {wait_time} seconds")
        
        await asyncio.sleep(wait_time + 1)  # +1 second extra safety
        return await app_bot.send_message(chat_id, text)
    
    except Exception as e:
        logger.error(f"❌ Send failed: {e}")
        return False

# ============ YOUR BOT COMMANDS ============
@app_bot.on_message(filters.command("start"))
async def start_command(client, message):
    await message.reply_text(
        "🤖 Bot is alive!\n"
        "Commands:\n"
        "/ping - Check bot status\n"
        "/status - Check bot health"
    )

@app_bot.on_message(filters.command("ping"))
async def ping_command(client, message):
    await message.reply_text("🏓 Pong! Bot is working fine.")

@app_bot.on_message(filters.command("status"))
async def status_command(client, message):
    await message.reply_text(
        "✅ Bot Status:\n"
        f"• Running: Yes\n"
        f"• Uptime: Active\n"
        f"• Keep-alive: Enabled"
    )

# ============ MAIN BOT FUNCTION ============
async def run_bot():
    """Bot ko start karein"""
    logger.info("🚀 Starting bot...")
    try:
        await app_bot.start()
        logger.info("✅ Bot started successfully!")
        
        # Bot info get karein
        bot_info = await app_bot.get_me()
        logger.info(f"🤖 Bot: @{bot_info.username}")
        
        # Yahan apna bot logic daalein
        # Example: Auto-message send karna
        # await safe_send_message(chat_id, "Hello!")
        
        # Bot ko continuously run karein
        await asyncio.Event().wait()  # Infinite wait
        
    except Exception as e:
        logger.error(f"❌ Bot failed: {e}")
    finally:
        await app_bot.stop()

# ============ MAIN ENTRY POINT ============
if __name__ == "__main__":
    logger.info("🔄 Starting application...")
    
    # 1. Flask server start karein (background thread)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("🌐 Flask server started on port 8080")
    
    # 2. Self-ping thread start karein
    ping_thread = threading.Thread(target=self_ping, daemon=True)
    ping_thread.start()
    logger.info("🔄 Self-ping started (every 5 minutes)")
    
    # 3. Bot run karein
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
