# server.py fayli (Render Webhook uchun moslashtirilgan)

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.methods import DeleteWebhook, SetWebhook

# Webhook serveri uchun kerakli importlar
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Handlerlar va API dan importlar
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

# Render uchun muhim Webhook sozlamalari
WEB_SERVER_HOST = "0.0.0.0"
# Render avtomatik ravishda PORT ENV'ni beradi
WEB_SERVER_PORT = int(os.environ.get("PORT", 8080)) 
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

# Buni Render Env Variables'iga kiritishingiz kerak
BASE_WEBHOOK_URL = os.environ.get("WEBHOOK_BASE_URL") 


if not BOT_TOKEN:
    logging.error("BOT_TOKEN Env Variablesida topilmadi! Bot ishga tushmaydi.")
if not BASE_WEBHOOK_URL:
    logging.error("WEBHOOK_BASE_URL Env Variablesida topilmadi! Webhook ishlamaydi.")


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
        # Agar credentials topilmasa, botni ishga tushirmaslik uchun xatolik ko'rsatamiz
        # Ammo aiohttp serverini to'xtatish murakkab, shuning uchun faqat log yozamiz.
        return 
        
    logging.info("Credentials muvaffaqiyatli sozlandi.")

    # 2. Telegramga Webhook URLni o'rnatish
    webhook_url = f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}"
    
    # Oldingi long pollingni o'chirish (Agar mavjud bo'lsa)
    await bot(DeleteWebhook(drop_pending_updates=True)) 
    
    # Yangi Webhook o'rnatish
    await bot.set_webhook(url=webhook_url)
    logging.info(f"Webhook muvaffaqiyatli o'rnatildi: {webhook_url}")

async def on_shutdown(bot: Bot):
    """Veb-server o'chganda bajariladigan amallar."""
    # Webhookni o'chirish
    await bot.delete_webhook()
    logging.info("Webhook o'chirildi.")


# --- V. ASOSIY WEBHOOK ISHGA TUSHIRISH FUNKSIYASI ---
async def main():
    if not bot or not dp or not BASE_WEBHOOK_URL:
        print("\nBot ishga tushirilmadi. Token/Base URL xato.\n")
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
    
    # Aiogram handlerini o'rnatish
    request_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=BOT_TOKEN, # Xavfsizlik uchun
    )
    
    # Webhook yo'lini o'rnatish
    request_handler.register(app, path=WEBHOOK_PATH)

    # Serverni sozlash va ishga tushirish
    setup_application(app, dp, bot=bot)
    logging.info(f"Veb-server ishga tushirilmoqda. Port: {WEB_SERVER_PORT}")
    
    await web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


if __name__ == "__main__":
    # Ogohlantirish (faqat agar Admin ID o'rnatilmagan bo'lsa)
    if 123456789 in ADMIN_IDS:
        print("\n!!! ESLATMA: Iltimos, ADMIN_IDS ni o'zingizning Telegram ID raqamingizga o'zgartiring. !!!\n")
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot to'xtatildi")
    except Exception as e:
        logging.error(f"Botda kutilmagan xato: {e}")
