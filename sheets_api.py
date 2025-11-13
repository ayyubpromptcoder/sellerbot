import gspread
import logging
from datetime import datetime
import itertools # Stokni guruhlash uchun

# config.py faylingizdan import qilingan deb faraz qilinadi
from config import SHEET_NAME, SHEET_NAMES 


# ==============================================================================
# I. UMUMIY YORDAMCHI FUNKSIYALAR
# ==============================================================================

def get_sheets_client():
    """Google Sheetsga ulanish. Agar xato bo'lsa None qaytaradi."""
    try:
        # 'service_account.json' faylini loyiha papkasiga joylash shart.
        gc = gspread.service_account(filename='service_account.json')
        # Bu yerda SHEETS_NAME o'rniga SPREADSHEET ID yoki link ishlatiladi.
        return gc.open_by_key(SHEET_NAME) 
    except Exception as e:
        logging.error(f"Google Sheetsga ulanishda xato: {e}")
        return None

def get_or_create_worksheet(spreadsheet, sheet_name, header_row):
    """Varaqni (worksheet) topadi, topilmasa, uni sarlavha qatori bilan yaratadi."""
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        # Yangi varaq yaratish
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=100, cols=20)
        # Sarlavhani birinchi qatorga yozish
        worksheet.append_row(header_row)
    return worksheet


# ==============================================================================
# II. SOTUVCHILAR (SELLERS) FUNKSIYALARI
# ==============================================================================

def get_all_sellers():
    """Sheetsdan barcha sotuvchilarni ro'yxat sifatida oladi (Admin uchun)."""
    spreadsheet = get_sheets_client()
    if not spreadsheet: return []
    
    try:
        worksheet = spreadsheet.worksheet(SHEET_NAMES["SELLERS"])
        # Sarlavhalarni tashlab yuboramiz
        return worksheet.get_all_values()[1:]  
    except gspread.WorksheetNotFound:
        return []
    except Exception as e:
        logging.error(f"Sotuvchilarni o'qishda xato: {e}")
        return []

def add_seller(seller_data):
    """Yangi sotuvchini Sheetsga qo'shadi (Admin FSM)."""
    spreadsheet = get_sheets_client()
    if not spreadsheet: return False
    
    try:
        worksheet = get_or_create_worksheet(
            spreadsheet, 
            SHEET_NAMES["SELLERS"], 
            header_row=["ID", "Sana", "Ism", "Mahalla", "Telefon", "Parol"]
        )
        
        current_rows = worksheet.get_all_values()
        new_id = len(current_rows) # Yangi IDni aniqlash
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        new_row = [
            new_id, 
            current_date,
            seller_data['seller_name'], 
            seller_data['seller_region'], 
            seller_data['seller_phone'], 
            seller_data['seller_password']
        ]
        
        worksheet.append_row(new_row)
        return True
    except Exception as e:
        logging.error(f"Sotuvchini yozishda xato: {e}")
        return False

def get_seller_by_id(seller_id):
    """ID orqali bitta sotuvchi ma'lumotini (qatorni) oladi (Admin navigatsiya uchun)."""
    spreadsheet = get_sheets_client()
    if not spreadsheet: return None
    
    try:
        worksheet = spreadsheet.worksheet(SHEET_NAMES["SELLERS"])
        all_sellers = worksheet.get_all_values()[1:] 
        
        # Sotuvchi IDsi 0-indeksda joylashgan
        for row in all_sellers:
            if len(row) > 0 and row[0] == str(seller_id):
                return row
        return None
    except Exception as e:
        logging.error(f"ID {seller_id} bo'yicha sotuvchini topishda xato: {e}")
        return None

def get_seller_by_password(password):
    """Parol orqali bitta sotuvchi ma'lumotini oladi (Sotuvchi botga ulanish uchun)."""
    spreadsheet = get_sheets_client()
    if not spreadsheet: return None
    
    try:
        worksheet = spreadsheet.worksheet(SHEET_NAMES["SELLERS"])
        all_sellers = worksheet.get_all_values()[1:]
        
        # Parol 5-indeksda joylashgan
        for row in all_sellers:
            if len(row) >= 6 and row[5] == str(password):
                return row
        return None
    except Exception as e:
        logging.error(f"Parol bo'yicha sotuvchini topishda xato: {e}")
        return None


# ==============================================================================
# III. MAHSULOTLAR (PRODUCTS) FUNKSIYALARI
# ==============================================================================

def get_all_products():
    """Sheetsdan barcha mahsulotlarni ro'yxat sifatida oladi (Admin uchun)."""
    spreadsheet = get_sheets_client()
    if not spreadsheet: return []
    
    try:
        worksheet = spreadsheet.worksheet(SHEET_NAMES["PRODUCTS"])
        return worksheet.get_all_values()[1:]
    except gspread.WorksheetNotFound:
        return []
    except Exception as e:
        logging.error(f"Mahsulotlarni o'qishda xato: {e}")
        return []

def add_product(name, price):
    """Yangi mahsulotni Sheetsga qo'shadi (Admin FSM)."""
    spreadsheet = get_sheets_client()
    if not spreadsheet: return False
    
    try:
        worksheet = get_or_create_worksheet(
            spreadsheet, 
            SHEET_NAMES["PRODUCTS"], 
            header_row=["ID", "Mahsulot Nomi", "Narxi"]
        )
        
        current_rows = worksheet.get_all_values()
        new_id = len(current_rows)
        
        worksheet.append_row([new_id, name, price])
        return True
    except Exception as e:
        logging.error(f"Mahsulotni qo'shishda xato: {e}")
        return False

def get_product_by_name(name):
    """Mahsulotni ism bo'yicha topadi va [ID, Nomi, Narxi] ni qaytaradi (Stock Issue FSM uchun)."""
    spreadsheet = get_sheets_client()
    if not spreadsheet: return None
    
    try:
        worksheet = spreadsheet.worksheet(SHEET_NAMES["PRODUCTS"])
        all_products = worksheet.get_all_values()[1:]
        
        normalized_name = name.strip().lower() 
        
        for row in all_products:
            if len(row) >= 2 and row[1].strip().lower() == normalized_name:
                return row
        return None
    except Exception as e:
        logging.error(f"Mahsulotni ism bo'yicha topishda xato: {e}")
        return None

def add_product_and_get_id(name, price):
    """Yangi mahsulotni qo'shadi va uning yangi ID sini qaytaradi (Stock Issue FSM uchun)."""
    spreadsheet = get_sheets_client()
    if not spreadsheet: return None
    
    try:
        worksheet = get_or_create_worksheet(
            spreadsheet, 
            SHEET_NAMES["PRODUCTS"], 
            header_row=["ID", "Mahsulot Nomi", "Narxi"]
        )
        
        current_rows = worksheet.get_all_values()
        new_id = len(current_rows)
        
        worksheet.append_row([new_id, name, price])
        return new_id
    except Exception as e:
        logging.error(f"Yangi mahsulot qo'shishda xato: {e}")
        return None

def get_product_name_by_id(product_id):
    """Mahsulot IDsi bo'yicha uning nomini qaytaradi (Stock View uchun)."""
    spreadsheet = get_sheets_client()
    if not spreadsheet: return f"ID: {product_id}" 
    
    try:
        worksheet = spreadsheet.worksheet(SHEET_NAMES["PRODUCTS"])
        all_products = worksheet.get_all_values()[1:] 

        for row in all_products:
            if row and row[0] == str(product_id):
                return row[1] 
        return f"ID: {product_id}"

    except Exception as e:
        logging.error(f"Mahsulot nomini ID bo'yicha olishda xato: {e}")
        return f"ID: {product_id}"


# ==============================================================================
# IV. STOK (STOCK) FUNKSIYALARI
# ==============================================================================

def add_stock_to_seller(seller_id, product_id, quantity, price):
    """Sotuvchiga berilgan tovarni Sheetsdagi Stok varag'iga yozadi (Stock Issue FSM uchun)."""
    spreadsheet = get_sheets_client()
    if not spreadsheet: return False
    
    try:
        worksheet = get_or_create_worksheet(
            spreadsheet, 
            SHEET_NAMES["STOCK"], 
            header_row=["ID", "Sotuvchi ID", "Mahsulot ID", "Soni", "Birlik Narxi", "Jami Narx", "Sana"]
        )
        
        total_price = float(price) * int(quantity)
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        new_row = [
            "", # Stok ID - gspread avtomatik qo'sha olmasligi mumkin, shuning uchun bo'sh qoldirish tavsiya etiladi yoki o'zingiz boshqaring
            seller_id, 
            product_id, 
            quantity, 
            price, 
            total_price,
            current_date
        ]
        
        worksheet.append_row(new_row)
        return True
    except Exception as e:
        logging.error(f"Stok ma'lumotini yozishda xato: {e}")
        return False

def get_seller_stock(seller_id):
    """Sotuvchi IDsi bo'yicha berilgan barcha tovarlarni qaytaradi va guruhlaydi (Stock View uchun)."""
    spreadsheet = get_sheets_client()
    if not spreadsheet: return None
    
    try:
        worksheet = spreadsheet.worksheet(SHEET_NAMES["STOCK"])
        all_stock = worksheet.get_all_values()[1:] 
        
        # 1. Tanlangan sotuvchining tovarlarini filtrlash
        seller_stock = [row for row in all_stock if len(row) > 1 and row[1] == str(seller_id)]
        
        if not seller_stock:
            return None

        # 2. Mahsulot ID si bo'yicha guruhlash va sonini hisoblash
        seller_stock.sort(key=lambda x: x[2])
        
        grouped_stock = {}
        for key, group in itertools.groupby(seller_stock, key=lambda x: x[2]):
            total_quantity = 0
            price = 0
            for item in group:
                try:
                    total_quantity += int(item[3]) 
                    price = item[4] 
                except ValueError:
                    continue
            
            # Faqat musbat sonli tovarlarni qaytarish
            if total_quantity > 0:
                grouped_stock[key] = (total_quantity, price) 
            
        return grouped_stock
        
    except Exception as e:
        logging.error(f"Sotuvchi stokini olishda xato: {e}")
        return None

# sheets_api.py da: V. SAVDO (SALES) FUNKSIYALARI (Yangi bo'lim)

def add_sale(seller_id, product_id, quantity, price):
    """Sotilgan tovarni Sheetsdagi SALES varag'iga yozadi."""
    spreadsheet = get_sheets_client()
    if not spreadsheet: return False
    
    try:
        worksheet = get_or_create_worksheet(
            spreadsheet, 
            SHEET_NAMES["SALES"], 
            header_row=["ID", "Sana", "Sotuvchi ID", "Mahsulot ID", "Soni", "Birlik Narxi", "Jami Tushum"]
        )
        
        total_price = float(price) * int(quantity)
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        new_row = [
            "", # ID
            current_date,
            seller_id, 
            product_id, 
            quantity, 
            price, 
            total_price
        ]
        
        worksheet.append_row(new_row)
        return True
    except Exception as e:
        logging.error(f"Savdo ma'lumotini yozishda xato: {e}")
        return False
