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
    
    url = "https://api.alerts.in.ua/v1/alerts/active.json"
    headers = {
        "Authorization": f"Bearer {ALERTS_API_TOKEN}"
    }
    
    logging.info("🚀 Точний моніторинг через API alerts.in.ua запущено.")

    async with ClientSession() as session:
        while True:
            try:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        alerts_list = data.get("alerts", [])
                        
                        # Шукаємо, чи є в активних тривогах Ніжин або Чернігівська область
                        is_alarm = False
                        for alert in alerts_list:
                            title = alert.get("location_title", "").lower()
                            oblast = alert.get("location_oblast", "").lower()
                            
                            if "ніжин" in title or "чернігів" in oblast or "чернігів" in title:
                                is_alarm = True
                                break
                        
                        current_status = "active" if is_alarm else "clear"
                            
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
                        body_err = await response.text()
                        logging.warning(f"⚠️ API alerts.in.ua повернув статус {response.status}: {body_err}")
            except Exception as e:
                logging.warning(f"❌ Помилка запиту до API alerts.in.ua: {e}")
            
            await asyncio.sleep(15)


async def handle_root_ping(request):
    return web.Response(text="Nizhyn Alert Bot is running 24/7! 🚀", content_type="text/plain")


async def setup_background_tasks(app):
    asyncio.create_task(check_alerts_api())


if __name__ == "__main__":
    app = web.Application()
    app.router.add_get("/", handle_root_ping)
    app.on_startup.append(setup_background_tasks)
    
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"Запуск веб-сервера на порті {port}...")
    web.run_app(app, host="0.0.0.0", port=port)
