# sheets_api.py ga qo'shiladigan funksiyalar

def get_all_sellers():
    """Sheetsdan barcha sotuvchilarni ro'yxat sifatida oladi."""
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
