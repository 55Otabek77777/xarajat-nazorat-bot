import pytesseract
from PIL import Image
import re

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_image(image_path):
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang="rus+eng")
    return text

def parse_check_data(text):
    lines = text.split("\n")
    items = []
    
    for line in lines:
        amounts = re.findall(r"\d[\d\s,\.]+", line)
        if amounts:
            for amount in amounts:
                clean_amount = amount.replace(" ", "").replace(",", "").replace(".", "")
                if len(clean_amount) >= 4:
                    try:
                        amount_val = float(clean_amount)
                        product = line.split(amount)[0].strip()
                        if not product:
                            product = "Mahsulot"
                        items.append({"product": product, "amount": amount_val})
                    except:
                        pass
    
    return items

def format_check_summary(items):
    if not items:
        return None, None, 0
    
    text = "📋 <b>Chekdan o'qildi:</b>\n\n"
    total = 0
    for i, item in enumerate(items, 1):
        text += f"{i}. {item['product']}: {item['amount']:,.0f} som\n"
        total += item["amount"]
    
    text += f"\n💰 <b>Jami: {total:,.0f} som</b>"
    return text, items, total
