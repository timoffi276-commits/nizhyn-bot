import os
import logging
import asyncio
from aiohttp import web, ClientSession

# --- НАЛАШТУВАННЯ ---
TELEGRAM_BOT_TOKEN = "9239792479:AAHn-MkZJtmlzYrrkRuya5DRkcMtVSFhNH0"
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
    
    logging.info("🚀 Моніторинг Ніжина через API запущено у фоновому режимі.")

    async with ClientSession() as session:
        # Тестове повідомлення при запуску нового бота
        await send_telegram_message(session, "🤖 **Бот моніторингу тривог успішно запущено і працює 24/7!**")

        while True:
            try:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        alerts_list = data.get("alerts", [])
                        
                        is_alarm = False
                        for alert in alerts_list:
                            title = alert.get("location_title", "").lower()
                            if "ніжин" in title:
                                is_alarm = True
                                break
                        
                        current_status = "active" if is_alarm else "clear"
                            
                        logging.info(f"🔎 Статус Ніжина: [{current_status.upper()}] (Попередній: [{last_alert_status}])")
                        
                        if last_alert_status is None:
                            last_alert_status = current_status
                            logging.info(f"📌 Початковий статус збережено: {current_status}")
                        
                        elif current_status != last_alert_status:
                            message_text = (
                                "🔴 **УВАГА! Повітряна тривога в Ніжинському районі!** Пройдіть в укриття!"
                                if current_status == "active"
                                else "🟢 **Відбій повітряної тривоги в Ніжинському районі.**Загроза минула."
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


async def start_background_tasks(app):
    app['alert_task'] = asyncio.create_task(check_alerts_api())


async def cleanup_background_tasks(app):
    app['alert_task'].cancel()
    await app['alert_task']


def init_app():
    app = web.Application()
    app.router.add_get("/", handle_root_ping)
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    return app


if __name__ == "__main__":
    app = init_app()
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)
