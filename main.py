import os
import logging
import asyncio
from aiohttp import web, ClientSession

# --- НАЛАШТУВАННЯ ---
TELEGRAM_BOT_TOKEN = "8924046656:AAFptNIBxDr-5MA773mF7OAdE2dJkfQEUkE"
CHANNEL_ID = "@nizhyn_life"

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


async def check_alert_status():
    global last_alert_status
    
    url = "https://neptun.in.ua/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    logging.info("🚀 Моніторинг Нептуна запущено (режим дебагу).")

    async with ClientSession() as session:
        while True:
            try:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        raw_text = await response.text()
                        
                        # Виводимо шматок HTML у логи, щоб побачити, що повертає сайт
                        logging.info(f"📄 HTML шматок з сайту: {raw_text[:350]}...")
                        
                        text_lower = raw_text.lower()
                        has_nizhyn = "ніжин" in text_lower
                        has_alarm = "тривога" in text_lower or "небезпека" in text_lower
                        has_clear = "відбій" in text_lower or "скасовано" in text_lower
                        
                        if has_alarm:
                            current_status = "active"
                        else:
                            current_status = "clear"
                            
                        logging.info(f"🔎 Статус району: [{current_status.upper()}] (Попередній: [{last_alert_status}])")
                        
                        if last_alert_status is None:
                            last_alert_status = current_status
                            logging.info(f"📌 Початковий статус збережено: {current_status}")
                        
                        elif current_status != last_alert_status:
                            message_text = (
                                "🔴 **УВАГА! Повітряна тривога в Ніжині та районі!** Пройдіть в укриття!"
                                if current_status == "active"
                                else "🟢 **Відбій повітряної тривоги в Ніжині та районі.** Загроза минула."
                            )
                            logging.info(f"⚡ ЗМІНА СТАТУСУ! Надсилаємо в {CHANNEL_ID}...")
                            await send_telegram_message(session, message_text)
                            last_alert_status = current_status
                    else:
                        logging.warning(f"⚠️ Нептун повернув статус: {response.status}")
            except Exception as e:
                logging.warning(f"❌ Помилка запиту до сайту: {e}")
            
            await asyncio.sleep(30)


async def handle_root_ping(request):
    return web.Response(text="Nizhyn Alert Bot is running 24/7! 🚀", content_type="text/plain")


async def setup_background_tasks(app):
    asyncio.create_task(check_alert_status())


if __name__ == "__main__":
    app = web.Application()
    app.router.add_get("/", handle_root_ping)
    app.on_startup.append(setup_background_tasks)
    
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"Запуск веб-сервера на порті {port}...")
    web.run_app(app, host="0.0.0.0", port=port)
