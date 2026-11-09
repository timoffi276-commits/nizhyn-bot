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

last_alert_type = None


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
    global last_alert_type
    
    url = "https://api.alerts.in.ua/v1/alerts/active.json"
    headers = {
        "Authorization": f"Bearer {ALERTS_API_TOKEN}"
    }
    
    logging.info("🚀 Моніторинг Ніжина запущено у фоновому режимі.")

    async with ClientSession() as session:
        await send_telegram_message(session, "🤖 **Бот моніторингу загрози БПЛА та ракет успішно запущено!**")

        while True:
            try:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        alerts_list = data.get("alerts", [])
                        
                        nizhyn_alert_type = "clear"
                        
                        for alert in alerts_list:
                            title = alert.get("location_title", "").lower()
                            if "ніжин" in title:
                                alert_type = alert.get("alert_type", "")
                                note = alert.get("note", "")
                                
                                logging.info(f"🚨 ДЕТАЛІ API -> alert_type: [{alert_type}] | note: [{note}]")
                                
                                alert_type_l = alert_type.lower()
                                note_l = note.lower()
                                
                                # Якщо в нотатці є слова про БПЛА/дрон — це жовтий (uav)
                                if "бпла" in note_l or "дрон" in note_l or "безпілотник" in note_l:
                                    nizhyn_alert_type = "uav"
                                # Якщо це air_raid або є слова про ракети/балістику — це червоний (missile)
                                else:
                                    nizhyn_alert_type = "missile"
                                break
                        
                        logging.info(f"🔎 Статус Ніжина: [{nizhyn_alert_type.upper()}] (Попередній: [{last_alert_type}])")
                        
                        # Ініціалізація при старті
                        if last_alert_type is None:
                            last_alert_type = nizhyn_alert_type
                            logging.info(f"📌 Початковий статус ініціалізовано: {nizhyn_alert_type}")
                        
                        # Зміна статусу
                        elif nizhyn_alert_type != last_alert_type:
                            if nizhyn_alert_type == "uav":
                                message_text = "🟡 **УВАГА! Ніжинський район-жовтий рівень небезпеки!** Пройдіть в укриття!⚠️"
                            elif nizhyn_alert_type == "missile":
                                message_text = "🔴 **УВАГА! Ніжинський район-червоний рівень небезпеки** 🚨 Пройдіть в укриття!"
                            else:
                                message_text = "🟢 **Відбій повітряної тривоги в Ніжинському районі.**"
                            
                            logging.info(f"⚡ ЗМІНА СТАТУСУ ({last_alert_type} -> {nizhyn_alert_type})! Надсилаємо в {CHANNEL_ID}...")
                            await send_telegram_message(session, message_text)
                            last_alert_type = nizhyn_alert_type
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
