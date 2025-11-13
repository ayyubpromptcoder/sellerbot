# admin_handlers.py
from aiogram import Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
import sheets_api
import logging

# --- I. FSM HOLATLARI BO'LIMI ---
class ProductForm(StatesGroup):
    waiting_for_product_name = State()
    waiting_for_product_price = State()

class SellerForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_region = State()
    waiting_for_phone = State()
    waiting_for_password = State()

# --- II. ASOSIY NAVIGATSIYA (START) BO'LIMI ---

# Yordamchi funksiya: Ruxsatni tekshirish
def is_admin(user_id):
    return user_id == ADMIN_ID

@CommandStart()
async def command_start_handler(message: types.Message):
    """/start buyrug'i uchun ishlov beruvchi."""
    if not is_admin(message.from_user.id):
        await message.answer("Siz administrator emassiz. Ruxsat yo'q.")
        return

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text="/mahsulot"),
                types.KeyboardButton(text="/sotuvchi")
            ]
        ],
        resize_keyboard=True
    )
    await message.answer("Assalomu alaykum, Admin! Asosiy buyruqlarni tanlang:", reply_markup=keyboard)


# --- III. MAHSULOTLAR BO'LIMI MANTIQI ---

@F.text == "/mahsulot"
async def handle_mahsulot(message: types.Message):
    """/mahsulot buyrug'i uchun ishlov beruvchi."""
    if not is_admin(message.from_user.id): return

    mahsulot_keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="📋 Mahsulotlar Ro'yxati", callback_data="list_products")],
            [types.InlineKeyboardButton(text="➕ Yangi Mahsulot Kiritish", callback_data="add_new_product")]
        ]
    )
    await message.answer("Mahsulotlar bo'limi:", reply_markup=mahsulot_keyboard)

@F.data == "list_products"
async def list_products(callback: types.CallbackQuery):
    """Mahsulotlar ro'yxatini Sheetsdan olib chiqarish."""
    if not is_admin(callback.from_user.id): return

    products = sheets_api.get_all_products()
    
    if products:
        response_text = "📋 **Barcha Mahsulotlar Ro'yxati:**\n\n"
        for row in products:
            if len(row) >= 3:
                 response_text += f"*{row[1]}*: {row[2]} so'm\n"
        await callback.message.answer(response_text, parse_mode="Markdown")
    else:
        await callback.message.answer("⚠️ Mahsulotlar bazasi bo'sh yoki ulanishda xato.")

    await callback.answer()

# Yangi Mahsulot Kiritish funksiyalari (FSM)
@F.data == "add_new_product"
async def start_add_product(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("Yangi mahsulot nomini kiriting:")
    await state.set_state(ProductForm.waiting_for_product_name)
    await callback.answer()

@ProductForm.waiting_for_product_name
async def process_product_name(message: types.Message, state: FSMContext):
    await state.update_data(product_name=message.text)
    await message.answer(f"'{message.text}' uchun narxni (faqat raqamda) kiriting:")
    await state.set_state(ProductForm.waiting_for_product_price)

@ProductForm.waiting_for_product_price
async def process_product_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
    except ValueError:
        await message.answer("Narx noto'g'ri kiritildi. Iltimos, faqat raqam kiriting:")
        return

    user_data = await state.get_data()
    product_name = user_data.get("product_name")

    if sheets_api.add_product(product_name, price):
        await message.answer(f"✅ Yangi mahsulot muvaffaqiyatli qo'shildi:\n"
                             f"Nomi: **{product_name}**\n"
                             f"Narxi: **{price}** so'm", parse_mode="Markdown")
    else:
        await message.answer("⚠️ Ma'lumotni Sheetsga yozishda xato yuz berdi. Konsolni tekshiring.")

    await state.clear()


# --- IV. SOTUVCHILAR BO'LIMI MANTIQI ---

@F.text == "/sotuvchi"
async def handle_sotuvchi(message: types.Message):
    """/sotuvchi buyrug'i uchun ishlov beruvchi."""
    if not is_admin(message.from_user.id): return

    sotuvchi_keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🛒 Sotuvchilardagi Mahsulotlar", callback_data="seller_stock_list")],
            [types.InlineKeyboardButton(text="👥 Sotuvchilar", callback_data="list_all_sellers_menu")],
            [types.InlineKeyboardButton(text="➕ Yangi Sotuvchi Qo'shish", callback_data="add_new_seller")]
        ]
    )
    await message.answer("Sotuvchilar bo'limi:", reply_markup=sotuvchi_keyboard)


# A. Yangi Sotuvchi Qo'shish Mantiqi (FSM) - O'zgarmas

@F.data == "add_new_seller"
async def start_add_seller(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("Yangi sotuvchining **Ismi/Familiyasini** kiriting:")
    await state.set_state(SellerForm.waiting_for_name)
    await callback.answer()

@SellerForm.waiting_for_name
async def process_seller_name(message: types.Message, state: FSMContext):
    await state.update_data(seller_name=message.text)
    await message.answer("Sotuvchining **Mahallasini** kiriting:")
    await state.set_state(SellerForm.waiting_for_region)

@SellerForm.waiting_for_region
async def process_seller_region(message: types.Message, state: FSMContext):
    await state.update_data(seller_region=message.text)
    await message.answer("Sotuvchining **Telefon nomerini** kiriting:")
    await state.set_state(SellerForm.waiting_for_phone)
    
@SellerForm.waiting_for_phone
async def process_seller_phone(message: types.Message, state: FSMContext):
    await state.update_data(seller_phone=message.text)
    await message.answer("Sotuvchi uchun maxsus **Parol**ni kiriting (bu ulanish uchun kalit bo'ladi):")
    await state.set_state(SellerForm.waiting_for_password)

@SellerForm.waiting_for_password
async def process_seller_password(message: types.Message, state: FSMContext):
    if len(message.text) < 4:
         await message.answer("Parol juda qisqa. Kamida 4 belgidan iborat parol kiriting:")
         return
         
    await state.update_data(seller_password=message.text)
    user_data = await state.get_data()
    
    if sheets_api.add_seller(user_data): 
        await message.answer(f"✅ Yangi sotuvchi muvaffaqiyatli qo'shildi:\n"
                             f"Ismi: **{user_data['seller_name']}**\n"
                             f"Paroli: **{user_data['seller_password']}** (Parolni yodda tuting!)", 
                             parse_mode="Markdown")
    else:
        await message.answer("⚠️ Sotuvchini Sheetsga yozishda xato yuz berdi. Konsolni tekshiring.")

    await state.clear()


# --- V. HANDLERLARNI ULASH FUNKSIYASI ---

def setup_admin_handlers(dp: Dispatcher):
    """Barcha admin handlerlarini Dispatcher ga ro'yxatdan o'tkazish."""
    # Start
    dp.message.register(command_start_handler, CommandStart())
    
    # Mahsulotlar
    dp.message.register(handle_mahsulot, F.text == "/mahsulot")
    dp.callback_query.register(list_products, F.data == "list_products")
    dp.callback_query.register(start_add_product, F.data == "add_new_product")
    dp.message.register(process_product_name, ProductForm.waiting_for_product_name)
    dp.message.register(process_product_price, ProductForm.waiting_for_product_price)
    
    # Sotuvchilar
    dp.message.register(handle_sotuvchi, F.text == "/sotuvchi")
    dp.callback_query.register(start_add_seller, F.data == "add_new_seller")
    dp.message.register(process_seller_name, SellerForm.waiting_for_name)
    dp.message.register(process_seller_region, SellerForm.waiting_for_region)
    dp.message.register(process_seller_phone, SellerForm.waiting_for_phone)
    dp.message.register(process_seller_password, SellerForm.waiting_for_password)
    
    # Yangi sotuvchilar funksiyalari shu yerga qo'shiladi...
