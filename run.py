# run.py

import asyncio
import logging
import os # Env Variables uchun qo'shildi!
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

# Handlerlar va API dan importlar
from admin_handlers import setup_admin_handlers
from seller_handlers import setup_seller_handlers # Sotuvchi handlerlarini qo'shing
from sheets_api import setup_gspread_credentials 

# Loglarni sozlash
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# --- I. ENV VARIABLES DAN O'QISH (config.py o'rniga) ---
# Env Variables Renderda o'rnatilgan deb faraz qilinadi
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_IDS_STR = os.environ.get('ADMIN_IDS', '').split(',')
ADMIN_IDS = [int(i.strip()) for i in ADMIN_IDS_STR if i.strip().isdigit()]

# Tekshirish
if not BOT_TOKEN:
    logging.error("BOT_TOKEN Env Variablesida topilmadi! Bot ishga tushmaydi.")
if not ADMIN_IDS:
     logging.warning("ADMIN_IDS Env Variablesida topilmadi yoki noto'g'ri formatda.")


# --- II. BOT VA DISPATCHERNI YARATISH (Faqat bir marta) ---
if BOT_TOKEN:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
else:
    # Agar token bo'lmasa, bot obyekti yaratilmaydi
    bot = None
    dp = None

# --- III. HANDLERLARNI ULASH ---
if dp:
    setup_admin_handlers(dp)
    setup_seller_handlers(dp) # Sotuvchi handlerlari ulandi


# --- IV. ASOSIY ISHGA TUSHIRISH FUNKSIYASI ---
async def main():
    if not bot or not dp:
        print("\nBot ishga tushirilmadi, BOT_TOKEN o'rnatilmagan!\n")
        return
        
    logging.info("--- Google Sheets Credentials sozlanmoqda... ---")
    
    # 1. Google Sheets Credentialsni sozlash (Render uchun muhim)
    if not setup_gspread_credentials():
        logging.error("Google Sheets credentials sozlanmadi! Bot faoliyatini to'xtatadi.")
        # Agar credentials topilmasa, to'xtatish
        return 
    
    logging.info("Credentials muvaffaqiyatli sozlandi.")
    logging.info(f"Bot ishga tushirildi (Admin IDs: {ADMIN_IDS_STR})")
    
    # Buyruqlarni sozlash
    await bot.set_my_commands([
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="mahsulot", description="Admin: Mahsulotlar bo'limi"),
        BotCommand(command="sotuvchi", description="Admin: Sotuvchilar bo'limi"),
        BotCommand(command="stok", description="Sotuvchi: Stokni ko'rish"), 
        BotCommand(command="savdo", description="Sotuvchi: Savdo kiritish"), 
    ])

    # Long Polling rejimida ishga tushirish
    await dp.start_polling(bot)


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
