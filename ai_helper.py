from google import genai
from google.genai import types
from config import GEMINI_API_KEY
from datetime import datetime
import pytz
import json

client = genai.Client(api_key=GEMINI_API_KEY)

def get_tashkent_time():
    tz = pytz.timezone("Asia/Tashkent")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def analyze_check_with_ai(image_path):
    prompt = """
Siz moliyaviy chek tahlilchisisiz. Rasmda savdo cheki bor.

VAZIFA: Faqat sotib olingan mahsulotlar va summalarini JSON formatida qaytaring.

QOIDALAR:
1. Faqat mahsulot nomlari va ularning yakuniy summalarini chiqaring
2. Telefon, sana, QR kod umumiy malumotlarni etiborsiz qoldiring
3. MUHIM: Barcha matnlarni LOTIN ALIFBOSIDA yozing (kiril emas!)
4. Mahsulot nomlarini transliteratsiya qiling
5. JSON: {"items": [{"product": "...", "amount": 123456}], "total": 123456}

Faqat JSON qaytaring, LOTIN ALIFBOSIDA!
"""
    
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(data=image_data, mime_type="image/jpeg"),
                        types.Part.from_text(text=prompt)
                    ]
                )
            ]
        )
        
        text = response.text.strip()
        
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        data = json.loads(text)
        data["timestamp"] = get_tashkent_time()
        return data
    except Exception as e:
        error_str = str(e)
        if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
            return {"error": "limit", "message": "AI limiti tugadi"}
        print(f"AI xatosi: {e}")
        return None

def format_ai_check_summary(data):
    if not data or "items" not in data:
        return None, None, 0
    
    text = f"📋 <b>AI Tahlili</b>\n🕒 {data['timestamp']}\n\n"
    for i, item in enumerate(data["items"], 1):
        text += f"{i}. {item['product']}: {item['amount']:,.0f} som\n"
    text += f"\n💰 <b>Jami: {data['total']:,.0f} som</b>"
    
    return text, data["items"], data["total"]
