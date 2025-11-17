# admin_handlers.py (Boshlanish qismi)
from aiogram import Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- TUZATISH: config.py o'rniga os dan foydalanish ---
# from config import ADMIN_ID # Bu qatorni o'chiring
import os # os kutubxonasini qo'shing
# --------------------------------------------------------

import sheets_api
import logging

from aiogram import Dispatcher, types, F, Router # Router ni import qiling
from aiogram.filters import CommandStart
# ... qolgan importlar ...

# Routerni e'lon qilish
admin_router = Router()

# --- I. FSM HOLATLARI BO'LIMI ---
class ProductForm(StatesGroup):
    waiting_for_product_name = State()
    waiting_for_product_price = State()

class SellerForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_region = State()
    waiting_for_phone = State()
    waiting_for_password = State()

class StockIssueForm(StatesGroup):
    """Sotuvchiga tovar berish jarayonining holatlari."""
    waiting_for_product_name = State() # Tovar nomi
    waiting_for_new_product_price = State() # Tovar yangi bo'lsa, narxi
    waiting_for_quantity = State() # Tovar soni

# Yordamchi funksiya: Ruxsatni tekshirish
# --- II. ASOSIY NAVIGATSIYA (START) BO'LIMI ---

# Yordamchi funksiya: Ruxsatni tekshirish
def is_admin(user_id):
    # ADMIN_IDS ro'yxati Env Variablesdan olinadi (run.py da o'rnatilgan). 
    # Xavfsizlik uchun, har safar tekshirish yaxshi.
    admin_ids_str = os.environ.get('ADMIN_IDS', '').split(',')
    admin_ids = [int(i.strip()) for i in admin_ids_str if i.strip().isdigit()]
    return user_id in admin_ids

# admin_handlers.py
# ... boshqa funksiyalar va FSMlar

# @CommandStart() # DEKORATORNI O'CHIRDIK!
@admin_router.message(CommandStart())
async def command_start_handler(message: types.Message):
    """/start buyrug'i uchun ishlov beruvchi."""
    if not is_admin(message.from_user.id):
        await message.answer("Siz administrator emassiz. Ruxsat yo'q.")
        return

    # ... qolgan mantiq

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

@admin_router.message(F.text == "/mahsulot")
async def handle_mahsulot(message: types.Message):
    """/mahsulot buyrug'i uchun ishlov beruvchi."""
    if not is_admin(message.from_user.id): return
    # ... qolgan mantiq
    mahsulot_keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="📋 Mahsulotlar Ro'yxati", callback_data="list_products")],
            [types.InlineKeyboardButton(text="➕ Yangi Mahsulot Kiritish", callback_data="add_new_product")]
        ]
    )
    await message.answer("Mahsulotlar bo'limi:", reply_markup=mahsulot_keyboard)

@admin_router.callback_query(F.data == "list_products")
async def list_products(callback: types.CallbackQuery):
    # ... funksiya mantiqi ...
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

@admin_router.callback_query(F.data == "add_new_product") # <-- BU QATORNI QO'SHING
async def start_add_product(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("Yangi mahsulot nomini kiriting:")
    await state.set_state(ProductForm.waiting_for_product_name)
    await callback.answer()

@admin_router.message(ProductForm.waiting_for_product_name)
async def process_product_name(message: types.Message, state: FSMContext):
    await state.update_data(product_name=message.text)
    await message.answer(f"'{message.text}' uchun narxni (faqat raqamda) kiriting:")
    await state.set_state(ProductForm.waiting_for_product_price)

@admin_router.message(ProductForm.waiting_for_product_price)
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

@admin_router.message(F.text == "/sotuvchi")
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


# A. Yangi Sotuvchi Qo'shish Mantiqi (FSM) - O'zgartirishlar

@admin_router.callback_query(F.data == "add_new_seller") # <- O'zgardi
async def start_add_seller(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("Yangi sotuvchining **Ismi/Familiyasini** kiriting:")
    await state.set_state(SellerForm.waiting_for_name)
    await callback.answer()

@admin_router.message(SellerForm.waiting_for_name) # <- O'zgardi
async def process_seller_name(message: types.Message, state: FSMContext):
    await state.update_data(seller_name=message.text)
    await message.answer("Sotuvchining **Tumanini** kiriting:")
    await state.set_state(SellerForm.waiting_for_region)

@admin_router.message(SellerForm.waiting_for_region) # <- O'zgardi
async def process_seller_region(message: types.Message, state: FSMContext):
    await state.update_data(seller_region=message.text)
    await message.answer("Sotuvchining **Telefon nomerini** kiriting:")
    await state.set_state(SellerForm.waiting_for_phone)
    
@admin_router.message(SellerForm.waiting_for_phone) # <- O'zgardi
async def process_seller_phone(message: types.Message, state: FSMContext):
    await state.update_data(seller_phone=message.text)
    await message.answer("Sotuvchi uchun maxsus **Parol**ni kiriting (bu ulanish uchun kalit bo'ladi):")
    await state.set_state(SellerForm.waiting_for_password)

@admin_router.message(SellerForm.waiting_for_password) # <- O'zgardi
async def process_seller_password(message: types.Message, state: FSMContext):
    if len(message.text) < 4:
        await message.answer("Parol juda qisqa. Kamida 4 belgidan iborat parol kiriting:")
        return
    # ... funksiya mantiqining qolgan qismi ...
         
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

# admin_handlers.py da: IV. SOTUVCHILAR BO'LIMI MANTIQI

@admin_router.callback_query(F.data.startswith("issue_stock:"))
async def start_issue_stock(callback: types.CallbackQuery, state: FSMContext):
    """Sotuvchiga tovar berish jarayonini boshlash."""
    if not is_admin(callback.from_user.id): return
    
    # callback_data dan sotuvchi ID sini ajratib olish
    seller_sheet_id = callback.data.split(":")[1]
    
    # Joriy sotuvchi ID sini FSM ga saqlash
    await state.update_data(current_seller_id=seller_sheet_id)
    
    await callback.message.answer("Sotuvchiga beriladigan **Tovar Nomini** kiriting:")
    await state.set_state(StockIssueForm.waiting_for_product_name)
    await callback.answer()

@admin_router.message(StockIssueForm.waiting_for_product_name)
async def process_stock_name(message: types.Message, state: FSMContext):
    """Tovar nomini qabul qilish va bazada tekshirish."""
    
    product_name = message.text.strip()
    
    # ------------------------------------------------------------
    # sheets_api dan mahsulotni ism bo'yicha topish
    product_data = sheets_api.get_product_by_name(product_name) 
    # ------------------------------------------------------------
    
    await state.update_data(current_product_name=product_name)
    
    if product_data:
        # Mahsulot bazada mavjud (Narxni so'ramaymiz)
        await state.update_data(product_id=product_data[0]) # IDni saqlash
        await state.update_data(product_price=product_data[2]) # Narxni saqlash
        await message.answer(f"Mahsulot bazadan topildi. Narxi: **{product_data[2]}** so'm.\n"
                             f"Endi bu mahsulotning **Sonini (miqdorini)** kiriting:")
        await state.set_state(StockIssueForm.waiting_for_quantity)
        
    else:
        # Mahsulot bazada mavjud emas (Narxni so'rash kerak)
        await message.answer(f"Mahsulot bazadan topilmadi. '{product_name}' ni yangi mahsulot sifatida qo'shish uchun **Narxini (faqat raqamda)** kiriting:")
        await state.set_state(StockIssueForm.waiting_for_new_product_price)


@admin_router.message(StockIssueForm.waiting_for_new_product_price)
async def process_new_product_price(message: types.Message, state: FSMContext):
    """Yangi mahsulot narxini qabul qilish va uni Sheetsga qo'shish."""
    try:
        new_price = float(message.text)
    except ValueError:
        await message.answer("Narx noto'g'ri kiritildi. Iltimos, faqat raqam kiriting:")
        return

    user_data = await state.get_data()
    product_name = user_data.get('current_product_name')
    
    # ------------------------------------------------------------
    # Yangi mahsulotni Sheetsga qo'shish
    product_id = sheets_api.add_product_and_get_id(product_name, new_price) 
    # ------------------------------------------------------------

    if product_id:
        # ID ni saqlab, Sonini so'rashga o'tish
        await state.update_data(product_id=product_id)
        await state.update_data(product_price=new_price)
        await message.answer(f"✅ Yangi mahsulot **{product_name}** narxi **{new_price}** so'm bilan bazaga kiritildi.\n"
                             f"Endi bu mahsulotning **Sonini (miqdorini)** kiriting:")
        await state.set_state(StockIssueForm.waiting_for_quantity)
    else:
        await message.answer("⚠️ Mahsulotni Sheetsga yozishda xato yuz berdi. Jarayon bekor qilindi.")
        await state.clear()


@admin_router.message(StockIssueForm.waiting_for_quantity)
async def process_stock_quantity(message: types.Message, state: FSMContext):
    """Tovar sonini qabul qilish va Sotuvchi hisobiga yozish."""
    try:
        quantity = int(message.text)
        if quantity <= 0: raise ValueError
    except ValueError:
        await message.answer("Miqdor noto'g'ri kiritildi. Iltimos, musbat butun son kiriting:")
        return
        
    user_data = await state.get_data()
    seller_id = user_data.get('current_seller_id')
    product_id = user_data.get('product_id')
    product_name = user_data.get('current_product_name')
    price = user_data.get('product_price')

    # ------------------------------------------------------------
    # Sotuvchi hisobiga tovar qo'shish
    if sheets_api.add_stock_to_seller(seller_id, product_id, quantity, price):
        await message.answer(f"✅ Sotuvchiga tovar berildi!\n"
                             f"Tovar: **{product_name}**\n"
                             f"Soni: **{quantity}** dona\n"
                             f"Narxi: **{price}** so'm", parse_mode="Markdown")
    else:
        await message.answer("⚠️ Tovar berishda xato yuz berdi. Konsolni tekshiring.")
        
    await state.clear()

# admin_handlers.py da: IV. SOTUVCHILAR BO'LIMI MANTIQI (Parollar va Ro'yxatlar)

# B. Sotuvchilar Ro'yxati va Parollar Mantiqi

@admin_router.callback_query(F.data == "list_all_sellers_menu")
async def list_all_sellers_menu(callback: types.CallbackQuery):
    """Sotuvchilar ro'yxati uchun ichki menyuni chiqarish."""
    if not is_admin(callback.from_user.id): return

    sellers_menu_keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="👥 Barcha Sotuvchilar", callback_data="list_all_sellers")],
            [types.InlineKeyboardButton(text="🗺️ Mahalla Bo'yicha", callback_data="list_sellers_by_region")],
            [types.InlineKeyboardButton(text="🔑 Sotuvchilar Parollari", callback_data="list_all_passwords")]
        ]
    )
    await callback.message.edit_text("Sotuvchilar ro'yxati variantlari:", reply_markup=sellers_menu_keyboard)
    await callback.answer()

@admin_router.callback_query(F.data == "list_all_passwords")
async def list_all_passwords(callback: types.CallbackQuery):
    """Barcha sotuvchilarning parollarini chiqarish."""
    if not is_admin(callback.from_user.id): return
    
    sellers = sheets_api.get_all_sellers()
    
    if sellers:
        response_text = "🔑 **Barcha Sotuvchilar Parollari:**\n\n"
        for row in sellers:
            if len(row) >= 6:
                name = row[2]
                password = row[5]
                response_text += f"*{name}*: `{password}`\n"

        await callback.message.answer(response_text, parse_mode="Markdown")
    else:
        await callback.message.answer("Sotuvchilar bazasi bo'sh.")
    await callback.answer()


@admin_router.callback_query(F.data == "list_all_sellers")
async def list_all_sellers(callback: types.CallbackQuery):
    """Barcha sotuvchilarni alifbo tartibida Inline Button sifatida chiqarish."""
    if not is_admin(callback.from_user.id): return
    
    sellers = sheets_api.get_all_sellers()
    
    if sellers:
        # Ism bo'yicha saralash
        sellers.sort(key=lambda x: x[2]) 
        
        keyboard_rows = []
        for seller in sellers:
            seller_id = seller[0] 
            seller_name = seller[2]
            keyboard_rows.append([types.InlineKeyboardButton(text=seller_name, callback_data=f"view_seller:{seller_id}")])

        all_sellers_keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        await callback.message.edit_text("👥 **Barcha Sotuvchilar Ro'yxati (Alifbo bo'yicha):**", reply_markup=all_sellers_keyboard)
    else:
        await callback.message.answer("Sotuvchilar bazasi bo'sh.")
    await callback.answer()


@admin_router.callback_query(F.data.startswith("view_seller:"))
async def view_seller_details(callback: types.CallbackQuery):
    """Tanlangan sotuvchi uchun maxsus menyu chiqarish."""
    if not is_admin(callback.from_user.id): return
    
    seller_sheet_id = callback.data.split(":")[1]
    seller_data = sheets_api.get_seller_by_id(seller_sheet_id) 

    if not seller_data:
        await callback.message.answer("Sotuvchi topilmadi.")
        return
        
    seller_name = seller_data[2]
    
    seller_details_keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="🛍️ Mahsulotlari va Narxlari", callback_data=f"seller_stock:{seller_sheet_id}")],
            [types.InlineKeyboardButton(text="➕ Sotuvchiga Yangi Tovar Berish", callback_data=f"issue_stock:{seller_sheet_id}")],
            [types.InlineKeyboardButton(text="🔑 Sotuvchi Paroli", callback_data=f"seller_password_view:{seller_sheet_id}")]
        ]
    )
    
    await callback.message.edit_text(f"**Sotuvchi: {seller_name}** uchun amallar:", reply_markup=seller_details_keyboard, parse_mode="Markdown")
    await callback.answer()
    

@admin_router.callback_query(F.data.startswith("seller_password_view:"))
async def view_single_password(callback: types.CallbackQuery):
    """Tanlangan sotuvchining parolini chiqarish."""
    if not is_admin(callback.from_user.id): return
    seller_sheet_id = callback.data.split(":")[1]
    
    seller_data = sheets_api.get_seller_by_id(seller_sheet_id) 
    
    if seller_data and len(seller_data) >= 6:
        name = seller_data[2]
        password = seller_data[5]
        await callback.message.answer(f"**{name}** ning paroli: `{password}`", parse_mode="Markdown")
    else:
        await callback.message.answer("Sotuvchi topilmadi yoki ma'lumot bazasida xato.")

    await callback.answer()

# --- V. HANDLERLARNI ULASH FUNKSIYASI ---

# --- V. HANDLERLARNI ULASH FUNKSIYASI ---

def setup_admin_handlers(dp: Dispatcher):
    """Barcha admin handlerlarini Dispatcher ga ro'yxatdan o'tkazish.
    Aiogram 3.x usulida, barcha handlerlar admin_router ichida dekoratorlar orqali
    aniqlangan bo'lishi kerak.
    """
    # Faqat Router ni Dispatcher ga ulaymiz.
    # dp.message.register() kabi eski usullar to'liq olib tashlandi.
    dp.include_router(admin_router)
# admin_handlers.py da: Qo'shilgan yangi funksiya

@admin_router.callback_query(F.data.startswith("seller_stock:"))
async def view_seller_stock(callback: types.CallbackQuery):
    """Sotuvchining jami stokini Sheetsdan olib chiqarish."""
    if not is_admin(callback.from_user.id): return
    
    seller_sheet_id = callback.data.split(":")[1]
    
    # ------------------------------------------------------------
    # sheets_api dan sotuvchi stokini olish
    grouped_stock = sheets_api.get_seller_stock(seller_sheet_id)
    seller_data = sheets_api.get_seller_by_id(seller_sheet_id)
    seller_name = seller_data[2] if seller_data else "Noma'lum sotuvchi"
    # ------------------------------------------------------------

    if grouped_stock:
        response_text = f"🛍️ **{seller_name}** dagi Jami Stok:\n\n"
        
        # Stokdagi har bir mahsulotni hisoblab chiqarish
        for product_id, (quantity, price) in grouped_stock.items():
            # Mahsulot IDsi orqali nomini olish
            product_name = sheets_api.get_product_name_by_id(product_id) 
            
            response_text += f"**{product_name}**:\n"
            response_text += f"   - Soni: `{quantity}` dona\n"
            response_text += f"   - Narxi: `{price}` so'm\n"
            
        await callback.message.answer(response_text, parse_mode="Markdown")
    else:
        await callback.message.answer(f"**{seller_name}** hisobida hozircha tovarlar mavjud emas.")

    await callback.answer()
    
    # Yangi sotuvchilar funksiyalari shu yerga qo'shiladi...


