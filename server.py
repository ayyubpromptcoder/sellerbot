# server.py fayli (Render Webhook uchun eng barqaror yechim)

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.methods import DeleteWebhook, SetWebhook

# Webhook serveri uchun kerakli importlar
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Handlerlar va API dan importlar (Loyihangizdagi fayllar)
from admin_handlers import setup_admin_handlers
from seller_handlers import setup_seller_handlers
from sheets_api import setup_gspread_credentials

# Loglarni sozlash
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- I. ENV VARIABLES DAN O'QISH VA WEBHOOK SOZLAMALARI ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_IDS_STR = os.environ.get('ADMIN_IDS', '').split(',')
ADMIN_IDS = [int(i.strip()) for i in ADMIN_IDS_STR if i.strip().isdigit()]

# Xavfsizlik tokeni (BOT_TOKENdan alohida bo'lishi kerak)
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", None) 

# Render uchun muhim Webhook sozlamalari
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = int(os.environ.get("PORT", 8080)) 
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}" # URL path bot tokeni orqali unique qilinadi
BASE_WEBHOOK_URL = os.environ.get("WEBHOOK_BASE_URL") 


if not BOT_TOKEN:
    logging.error("BOT_TOKEN Env Variablesida topilmadi! Bot ishga tushmaydi.")
if not BASE_WEBHOOK_URL:
    logging.error("WEBHOOK_BASE_URL Env Variablesida topilmadi! Webhook ishlamaydi.")
if not WEBHOOK_SECRET: 
    logging.error("WEBHOOK_SECRET Env Variablesida topilmadi! Webhook xavfsiz bo'lmaydi.")


# --- II. BOT VA DISPATCHERNI YARATISH ---
if BOT_TOKEN:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
else:
    bot = None
    dp = None

# --- III. HANDLERLARNI ULASH ---
if dp:
    setup_admin_handlers(dp)
    setup_seller_handlers(dp)


# --- IV. WEBHOOK STARTUP VA SHUTDOWN FUNKSIYALARI ---
async def on_startup(bot: Bot):
    """Veb-server ishga tushganda bajariladigan amallar."""
    
    # 1. Google Sheets Credentialsni sozlash
    if not setup_gspread_credentials():
        logging.error("Google Sheets credentials sozlanmadi! Bot ishlamaydi.")
        return 
        
    logging.info("Credentials muvaffaqiyatli sozlandi.")

    # 2. Telegramga Webhook URLni o'rnatish
    webhook_url = f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}"
    
    # Oldingi long pollingni o'chirish
    await bot(DeleteWebhook(drop_pending_updates=True)) 
    
    # Yangi Webhook o'rnatish, WEBHOOK_SECRET bilan birga
    await bot.set_webhook(url=webhook_url, secret_token=WEBHOOK_SECRET) 
    
    logging.info(f"Webhook muvaffaqiyatli o'rnatildi: {webhook_url}")

async def on_shutdown(bot: Bot):
    """Veb-server o'chganda bajariladigan amallar."""
    # Webhookni o'chirish
    await bot.delete_webhook()
    logging.info("Webhook o'chirildi.")


# --- V. ASOSIY WEBHOOK ISHGA TUSHIRISH FUNKSIYASI ---
async def main():
    if not bot or not dp or not BASE_WEBHOOK_URL or not WEBHOOK_SECRET: 
        print("\nBot ishga tushirilmadi. Kerakli Env Variables topilmadi.\n")
        return
        
    logging.info("--- Webhook rejimida ishga tushirish boshlandi ---")

    # Startup/Shutdown funksiyalarini ulash
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Buyruqlarni sozlash
    await bot.set_my_commands([
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="mahsulot", description="Admin: Mahsulotlar bo'limi"),
        BotCommand(command="sotuvchi", description="Admin: Sotuvchilar bo'limi"),
        BotCommand(command="stok", description="Sotuvchi: Stokni ko'rish"), 
        BotCommand(command="savdo", description="Sotuvchi: Savdo kiritish"), 
    ])

    # Aiohttp serverini sozlash
    app = web.Application()
    
    # Request Handler'ni o'rnatish
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET, # Secretni tekshirish uchun ishlatiladi
    )
    
    # Webhook yo'lini o'rnatish 
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    # Dispatcher va Botni app'ga ulash 
    setup_application(app, dp, bot=bot)
    
    # Serverni to'g'ri ishga tushirish va Event Loop bilan aralashmaslik
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_SERVER_HOST, WEB_SERVER_PORT)
    await site.start()
    
    logging.info(f"Veb-server ishga tushirildi. Host: {WEB_SERVER_HOST}, Port: {WEB_SERVER_PORT}")

    # Serverni cheksiz ishlashini ta'minlash (Render uchun muhim)
    await asyncio.Event().wait()


if __name__ == "__main__":
    # Ogohlantirish
    if 123456789 in ADMIN_IDS:
        print("\n!!! ESLATMA: Iltimos, ADMIN_IDS ni o'zingizning Telegram ID raqamingizga o'zgartiring. !!!\n")
        
    try:
        # Event Loop'ni boshqarishning barqaror usuli
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
        
    except KeyboardInterrupt:
        logging.info("Bot to'xtatildi")
    except Exception as e:
        # Kutilmagan xatolarni logga yozish
        logging.error(f"Botda kutilmagan xato: {e}", exc_info=True)
