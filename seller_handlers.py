# seller_handlers.py
from aiogram import Dispatcher, types, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import sheets_api
import logging

# Routerni e'lon qilish
router = Router()

# ==============================================================================
# I. FSM HOLATLARI BO'LIMI
# ==============================================================================

class AuthForm(StatesGroup):
    """Sotuvchining botga parol orqali ulanish holatlari."""
    waiting_for_password = State()

class SaleForm(StatesGroup):
    """Sotuv amalga oshirish (yangi savdo kiritish) holatlari."""
    waiting_for_product_name = State() # Sotilgan mahsulot nomi
    waiting_for_quantity = State()     # Sotilgan mahsulot soni

# ==============================================================================
# II. YORDAMCHI FUNKSIYALAR
# ==============================================================================

async def is_seller_authenticated(user_id, state: FSMContext) -> bool:
    """Foydalanuvchi sotuvchi sifatida tizimga kirganligini tekshiradi."""
    user_data = await state.get_data()
    # FSMContextda 'seller_id' mavjud bo'lsa, tizimga kirgan hisoblanadi.
    if user_data.get('seller_id'):
        return True
    return False


# ==============================================================================
# III. ASOSIY NAVIGATSIYA (START) BO'LIMI
# ==============================================================================

@router.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext):
    """/start buyrug'i uchun ishlov beruvchi (Birlamchi kirish)."""
    
    # 1. Tizimga kirilganmi?
    if await is_seller_authenticated(message.from_user.id, state):
        
        user_data = await state.get_data()
        seller_name = user_data.get('seller_name', "Sotuvchi")
        
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [
                    types.KeyboardButton(text="🛍️ Stokni ko'rish"),
                    types.KeyboardButton(text="🛒 Savdo kiritish")
                ],
                [
                    types.KeyboardButton(text="🚪 Chiqish")
                ]
            ],
            resize_keyboard=True
        )
        await message.answer(f"Assalomu alaykum, **{seller_name}**! Asosiy menyu:", 
                             reply_markup=keyboard, parse_mode="Markdown")
        
    else:
        # 2. Tizimga kirmagan bo'lsa, parolni so'rash
        await message.answer("Tizimga kirish uchun maxsus **Parol**ni kiriting.")
        await state.set_state(AuthForm.waiting_for_password)


# ==============================================================================
# IV. AVTORIZATSIYA MANTIQI
# ==============================================================================

@router.message(AuthForm.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    """Foydalanuvchi kiritgan parolni tekshirish."""
    password = message.text.strip()
    
    # Parolni tekshirish uchun sheets_api.py dagi funksiyadan foydalanamiz
    seller_data = sheets_api.get_seller_by_password(password)
    
    if seller_data:
        # Tizimga muvaffaqiyatli kirish
        seller_id = seller_data[0]
        seller_name = seller_data[2]
        
        # FSM ga ma'lumotlarni saqlash
        await state.update_data(seller_id=seller_id, seller_name=seller_name)
        
        # Asosiy menyuni chiqarish
        await state.clear()
        await command_start_handler(message, state) # Menyu uchun start handlerga qaytish
        
    else:
        await message.answer("❌ Parol noto'g'ri. Iltimos, qayta urining yoki adminga murojaat qiling.")

# seller_handlers.py da: V. HANDLERLARNI ULASH FUNKSIYASIDAN OLDIN

# ==============================================================================
# V. STOK MANTIQI
# ==============================================================================

@router.message(F.text == "🛍️ Stokni ko'rish")
async def view_seller_stock(message: types.Message, state: FSMContext):
    """Sotuvchining o'zidagi mavjud tovarlar ro'yxatini chiqarish."""
    if not await is_seller_authenticated(message.from_user.id, state):
        await message.answer("Iltimos, avval tizimga kiring.")
        return
        
    user_data = await state.get_data()
    seller_id = user_data.get('seller_id')
    seller_name = user_data.get('seller_name')
    
    # Sheets API orqali sotuvchining stokini olish (Admin botida ishlatgan funksiya)
    stock_data = sheets_api.get_seller_stock(seller_id)
    
    response_text = f"🛍️ **{seller_name}** dagi Mahsulotlar Ro'yxati:\n\n"
    
    if stock_data:
        # stock_data = {product_id: (quantity, price), ...}
        for product_id, (quantity, price) in stock_data.items():
            
            # Agar mahsulot miqdori 0 yoki undan kam bo'lsa, ko'rsatmaslik
            if int(quantity) <= 0:
                continue
                
            product_name = sheets_api.get_product_name_by_id(product_id)
            
            response_text += (f"• *{product_name}*: **{quantity}** dona (@ {price} so'm)\n")
        
        await message.answer(response_text, parse_mode="Markdown")
        
    else:
        await message.answer(f"**{seller_name}** hisobida hozircha tovarlar mavjud emas.", parse_mode="Markdown")

    await message.answer("Davom etish uchun menyudan tanlang.")


# ==============================================================================
# V. HANDLERLARNI ULASH FUNKSIYASI (Router bilan)
# ==============================================================================

def setup_seller_handlers(dp: Dispatcher):
    """Barcha sotuvchi handlerlarini Dispatcher ga ro'yxatdan o'tkazish."""
    dp.include_router(router)

# seller_handlers.py da: V. STOK MANTIQIDAN KEYIN

# ==============================================================================
# VI. SAVDO KIRITISH MANTIQI (SaleForm FSM)
# ==============================================================================

@router.message(F.text == "🛒 Savdo kiritish")
async def start_sale_entry(message: types.Message, state: FSMContext):
    """Savdo kiritish jarayonini boshlash."""
    if not await is_seller_authenticated(message.from_user.id, state):
        await message.answer("Iltimos, avval tizimga kiring.")
        return
        
    await message.answer("Sotilgan **Mahsulot Nomini** kiriting:")
    await state.set_state(SaleForm.waiting_for_product_name)


@router.message(SaleForm.waiting_for_product_name)
async def process_sale_product_name(message: types.Message, state: FSMContext):
    """Sotilgan mahsulot nomini qabul qilish."""
    product_name = message.text.strip()
    
    # Mahsulotni Sheets API da tekshirish (narxini olish uchun)
    product_data = sheets_api.get_product_by_name(product_name)
    
    if not product_data:
        await message.answer(f"❌ '{product_name}' nomli mahsulot bazada topilmadi. Nomni to'g'ri kiritganingizga ishonch hosil qiling:")
        return

    product_id = product_data[0]
    product_price = product_data[2] # Mahsulotning birlik narxi
    
    # Ma'lumotlarni saqlash
    await state.update_data(current_product_id=product_id, 
                            current_product_name=product_name, 
                            current_product_price=product_price)
    
    await message.answer(f"Mahsulot narxi: **{product_price}** so'm.\nEndi sotilgan **Miqdorni (sonini)** kiriting:")
    await state.set_state(SaleForm.waiting_for_quantity)


@router.message(SaleForm.waiting_for_quantity)
async def process_sale_quantity(message: types.Message, state: FSMContext):
    """Sotilgan miqdorni qabul qilish va savdoni Sheetsga yozish."""
    try:
        quantity = int(message.text)
        if quantity <= 0: raise ValueError
    except ValueError:
        await message.answer("Miqdor noto'g'ri kiritildi. Iltimos, musbat butun son kiriting:")
        return
        
    user_data = await state.get_data()
    seller_id = user_data.get('seller_id')
    product_id = user_data.get('current_product_id')
    product_name = user_data.get('current_product_name')
    price = user_data.get('current_product_price')
    
    # 1. Savdoni "SALES" varag'iga yozish
    if sheets_api.add_sale(seller_id, product_id, quantity, price):
        
        # 2. Stokdan ushbu miqdorni ayirib tashlash (Stok varag'iga manfiy qiymat yoziladi)
        # add_stock_to_seller funksiyasidan foydalanamiz, lekin manfiy miqdorni beramiz.
        negative_quantity = -quantity
        
        if sheets_api.add_stock_to_seller(seller_id, product_id, negative_quantity, price):
            total_sale = quantity * float(price)
            await message.answer(f"✅ Savdo muvaffaqiyatli kiritildi!\n"
                                 f"Tovar: **{product_name}**\n"
                                 f"Sotildi: **{quantity}** dona\n"
                                 f"Jami qiymat: **{total_sale:,.2f}** so'm", parse_mode="Markdown")
        else:
            await message.answer("⚠️ Savdo yozildi, lekin stokdan ayirishda xato yuz berdi. Adminga xabar bering.")
            
    else:
        await message.answer("⚠️ Savdoni Sheetsga yozishda xato yuz berdi. Jarayon bekor qilindi.")

    await state.clear()
    await command_start_handler(message, state) # Asosiy menyuga qaytish


# ==============================================================================
# VII. CHIQISH MANTIQI (LOGOUT)
# ==============================================================================

@router.message(F.text == "🚪 Chiqish")
async def handle_logout(message: types.Message, state: FSMContext):
    """Sotuvchini tizimdan chiqarish."""
    await state.clear()
    
    # Maxfiy (ReplyKeyboardRemove) klaviaturani yuborish
    remove_keyboard = types.ReplyKeyboardRemove()
    
    await message.answer("Siz tizimdan muvaffaqiyatli chiqdingiz. Qayta kirish uchun /start buyrug'ini yuboring.",
                         reply_markup=remove_keyboard)
