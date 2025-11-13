# run.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import BotCommand
from config import TELEGRAM_TOKEN_ADMIN, ADMIN_ID
from admin_handlers import setup_admin_handlers

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

# --- BOTNI YARATISH ---
bot = Bot(token=TELEGRAM_TOKEN_ADMIN)
dp = Dispatcher()

# --- HANDLERLARNI ULASH ---
setup_admin_handlers(dp)

async def main():
    logging.info("Admin Bot ishga tushirildi (Long Polling)...")
    
    # Buyruqlarni sozlash
    await bot.set_my_commands([
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="mahsulot", description="Mahsulotlar bo'limi"),
        BotCommand(command="sotuvchi", description="Sotuvchilar bo'limi"),
    ])

    # Agar Webhook qilib ishlatmoqchi bo'lsak, bu qism o'zgaradi.
    # Long Polling rejimida ishga tushirish
    await dp.start_polling(bot)

if __name__ == "__main__":
    
    if ADMIN_ID == 123456789:
        print("\n!!! ESLATMA: Iltimos, ADMIN_ID ni o'zingizning Telegram ID raqamingizga o'zgartiring. !!!\n")
        
    asyncio.run(main())
