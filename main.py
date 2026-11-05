import os
import logging
import asyncio
from aiohttp import web, ClientSession

# --- НАЛАШТУВАННЯ ---
TELEGRAM_BOT_TOKEN = "8924046656:AAFptNIBxDr-5MA773mF7OAdE2dJkfQEUkE"
CHANNEL_ID = "@nizhyn_life"
ALERTS_API_TOKEN = "fe2f8043ea50d7fc116cb410bb6478bc858ee08fab2203"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

last_alert_status = None


async def send_telegram_message(session, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        async with session.post(url, json=payload, timeout=10) as resp:
            if resp.status == 200:
                logging.info("✅ Сповіщення успішно надіслано в Telegram-канал!")
            else:
                body = await resp.text()
                logging.error(f"❌ Помилка Telegram API [{resp.status}]: {body}")
    except Exception as e:
        logging.error(f"❌ Помилка мережі при відправці в Telegram: {e}")


async def check_alerts_api():
    global last_alert_status
