import gspread
import logging
from datetime import datetime
import itertools
import os
import json 

# Logging sozlamalari
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- ENV VARIABLES dan yuklash ---
SHEET_NAME = os.environ.get('SHEET_NAME')
GSPREAD_CREDENTIALS_JSON = os.environ.get('GSPREAD_CREDENTIALS') 

if not SHEET_NAME:
    logging.error("SHEET_NAME atrof-muhit o'zgaruvchisi topilmadi.")

# Sheets nomlari
SHEET_NAMES = {
    "SELLERS": "Sotuvchilar",
    "PRODUCTS": "Mahsulotlar",
    "STOCK": "Stok",
    "SALES": "Savdolar"
}

# --- YORDAMCHI FUNKSIYA: JSON FAYLINI YARATISH ---
def setup_gspread_credentials():
    """GSPREAD_CREDENTIALS Env Variablesidan JSON faylini yaratadi."""
    if GSPREAD_CREDENTIALS_JSON:
        try:
            # Agar fayl nomi kerak bo'lsa, 'service_account.json' ni ishlatish
            file_path = 'service_account.json'
            
            # JSON stringni faylga yozish
            with open(file_path, 'w') as f:
                f.write(GSPREAD_CREDENTIALS_JSON)
                
            logging.info("service_account.json fayli ENV orqali yaratildi.")
            return True
        except Exception as e:
            logging.error(f"Credentials JSONni yozishda xato: {e}")
            return False
    
    if not os.path.exists('service_account.json'):
        logging.warning("GSPREAD_CREDENTIALS ENV va service_account.json fayli topilmadi.")
        return False
    return True

# ==============================================================================
# I. UMUMIY YORDAMCHI FUNKSIYALAR
# ==============================================================================

def get_sheets_client():
    """Google Sheetsga ulanish. Agar xato bo'lsa None qaytaradi."""
    if not SHEET_NAME: return None
    
    # 1. Credentialsni o'rnatishni bir marta tekshirish 
    if not setup_gspread_credentials():
        return None
        
    try:
        # Endi gspread.service_account 'service_account.json' ni topadi
        gc = gspread.service_account(filename='service_account.json')
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

def get_seller_name_by_id(seller_id):
    """Sotuvchi IDsi bo'yicha uning Ismini (Name) qaytaradi (Varq sarlavhalari uchun)."""
    seller_row = get_seller_by_id(seller_id)
    # Sotuvchi Ismi 1-indeksda joylashgan: [ID, Ism, Tuman, Telefon, Parol, Sana]
    return seller_row[1] if seller_row and len(seller_row) > 1 else str(seller_id)

def add_seller(seller_data):
    """Yangi sotuvchini Sheetsga qo'shadi (Admin FSM)."""
    spreadsheet = get_sheets_client()
    if not spreadsheet: return False
    
    try:
        worksheet = get_or_create_worksheet(
            spreadsheet, 
            SHEET_NAMES["SELLERS"], 
            # YANGILANGAN: "Mahalla" o'rniga "Tuman" ishlatildi va Sana oxirda
            header_row=["ID", "Ism", "Tuman", "Telefon", "Parol", "Sana"] 
        )
        
        current_rows = worksheet.get_all_values()
        new_id = len(current_rows) # Yangi IDni aniqlash
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # YANGILANGAN: Ma'lumotlar tartibi yangi sarlavhaga moslandi
        new_row = [
            new_id, 
            seller_data['seller_name'], 
            seller_data['seller_region'], # seller_region ma'lumoti Tuman ustuniga yoziladi
            seller_data['seller_phone'], 
            seller_data['seller_password'], 
            current_date
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
        
        # Parol 4-indeksda joylashgan: [ID, Ism, Tuman, Telefon, Parol, Sana]
        for row in all_sellers:
            if len(row) >= 5 and row[4] == str(password):
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
            # Sarlavha: Kilogrammi, Narxi, Sana oxirida
            header_row=["ID", "Sotuvchi", "Mahsulot ID", "Kilogrammi", "Narxi", "Jami Narx", "Sana"]
        )
        
        total_price = float(price) * int(quantity)
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Qator tuzilishi: [ID, Sotuvchi ID (1), Mahsulot ID (2), Kilogrammi (3), Narxi (4), Jami Narx (5), Sana (6)]
        new_row = [
            "", # ID 
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
        
        # Row formati: [ID(0), Sotuvchi ID(1), Mahsulot ID(2), Kilogrammi(3), Narxi(4), Jami Narx(5), Sana(6)]
        
        # 1. Tanlangan sotuvchining tovarlarini filtrlash
        seller_stock = [row for row in all_stock if len(row) > 1 and row[1] == str(seller_id)]
        
        if not seller_stock:
            return None

        # 2. Mahsulot ID si bo'yicha guruhlash va Kilogrammini hisoblash
        seller_stock.sort(key=lambda x: x[2]) # Mahsulot ID 2-indeksda
        
        grouped_stock = {}
        for key, group in itertools.groupby(seller_stock, key=lambda x: x[2]):
            total_quantity = 0
            price = 0
            for item in group:
                try:
                    total_quantity += int(item[3])  # Kilogrammi 3-indeksda
                    price = item[4]                 # Narxi 4-indeksda
                except ValueError:
                    continue
            
            # Faqat musbat sonli tovarlarni qaytarish
            if total_quantity > 0:
                grouped_stock[key] = (total_quantity, price) 
            
        return grouped_stock
        
    except Exception as e:
        logging.error(f"Sotuvchi stokini olishda xato: {e}")
        return None

# ==============================================================================
# V. SAVDO (SALES) FUNKSIYALARI
# ==============================================================================

def add_sale(seller_id, product_id, quantity, price):
    """Sotilgan tovarni Sheetsdagi SALES varag'iga yozadi."""
    spreadsheet = get_sheets_client()
    if not spreadsheet: return False
    
    try:
        worksheet = get_or_create_worksheet(
            spreadsheet, 
            SHEET_NAMES["SALES"], 
            # Sarlavha: Kilogrammi, Narxi, Sana oxirida
            header_row=["ID", "Sotuvchi", "Mahsulot ID", "Kilogrammi", "Narxi", "Jami Tushum", "Sana"]
        )
        
        total_price = float(price) * int(quantity)
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Yangi qator tuzilishi: [ID, Sotuvchi(1), Mahsulot ID(2), Kilogrammi(3), Narxi(4), Jami Tushum(5), Sana(6)]
        new_row = [
            "", # ID (Index 0)
            seller_id, # Sotuvchi ID (Index 1)
            product_id, # Mahsulot ID (Index 2)
            quantity, # Kilogrammi (Index 3)
            price, # Narxi (Index 4)
            total_price, # Jami Tushum (Index 5)
            current_date # Sana (Index 6) - Oxiriga ko'chirildi
        ]
        
        worksheet.append_row(new_row)
        return True
    except Exception as e:
        logging.error(f"Savdo ma'lumotini yozishda xato: {e}")
        return False

# ==============================================================================
# VI. HISOBOTLAR (REPORTS) FUNKSIYALARI
# ==============================================================================

def get_seller_sales_summary(seller_id, start_date=None, end_date=None):
    """
    Belgilangan sotuvchining (seller_id) savdo natijalarini (jami kilogrammi va tushumi)
    ko'rsatilgan sanalar oralig'ida hisoblaydi.
    """
    spreadsheet = get_sheets_client()
    if not spreadsheet: return {'total_quantity': 0, 'total_revenue': 0}

    # Sanani parselash yordamchi funksiyasi
    def parse_date(date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            # Agar format mos kelmasa, vaqtni e'tiborga olmasdan faqat sanani olish
            try:
                return datetime.strptime(date_str.split(' ')[0], "%Y-%m-%d")
            except:
                return None
    
    # Kiritilgan sana oralig'ini tayyorlash
    start_dt = parse_date(start_date) if start_date else None
    end_dt = parse_date(end_date) if end_date else None
    
    total_quantity = 0
    total_revenue = 0.0

    try:
        worksheet = spreadsheet.worksheet(SHEET_NAMES["SALES"])
        all_sales = worksheet.get_all_values()[1:]
        
        # Yangi Row formati: [ID(0), Sotuvchi(1), Mahsulot ID(2), Kilogrammi(3), Narxi(4), Jami Tushum(5), Sana(6)]
        
        for row in all_sales:
            if len(row) < 7: # Endi kamida 7 ustun bo'lishi kerak
                continue

            current_seller_id = row[1] # Sotuvchi ID endi 1-indeksda
            sale_date_str = row[6]      # Sana endi 6-indeksda (oxirida)
            
            # 1. Sotuvchini filtrlash
            if current_seller_id != str(seller_id):
                continue

            # 2. Sanani filtrlash (Agar start_dt yoki end_dt berilgan bo'lsa)
            sale_dt = parse_date(sale_date_str)
            if sale_dt:
                if start_dt and sale_dt < start_dt:
                    continue
                if end_dt and sale_dt > end_dt:
                    continue
            
            # 3. Hisoblash
            try:
                quantity = int(row[3]) # Kilogrammi endi 3-indeksda
                revenue = float(row[5]) # Jami Tushum endi 5-indeksda
                
                total_quantity += quantity
                total_revenue += revenue
            except ValueError:
                logging.warning(f"Savdo qatoridagi miqdor yoki tushum noto'g'ri formatda: {row}")
                continue
                
        return {
            'total_quantity': total_quantity,
            'total_revenue': round(total_revenue, 2)
        }
        
    except gspread.WorksheetNotFound:
        logging.warning(f"'{SHEET_NAMES['SALES']}' varag'i topilmadi. Hisobot bo'sh.")
        return {'total_quantity': 0, 'total_revenue': 0}
    except Exception as e:
        logging.error(f"Savdo hisobotini olishda xato: {e}")
        return {'total_quantity': 0, 'total_revenue': 0}
