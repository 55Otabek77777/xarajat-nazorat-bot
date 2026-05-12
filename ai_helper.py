import google.genai as genai
from config import GEMINI_API_KEYS, GEMINI_MODELS
import base64
import json
import re

# API key va model index
current_key_index = 0
current_model_index = 0

def get_next_model():
    """Keyingi modelga o'tish"""
    global current_model_index
    current_model_index = (current_model_index + 1) % len(GEMINI_MODELS)
    return GEMINI_MODELS[current_model_index]

def init_gemini():
    """Gemini'ni ishga tushirish"""
    genai.configure(api_key=GEMINI_API_KEYS[current_key_index])

def transliterate_to_latin(text):
    """Kiril -> Lotin"""
    kiril_latin = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'x', 'ц': 's', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh', 'ъ': '',
        'ы': 'i', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'J', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'X', 'Ц': 'S', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sh', 'Ъ': '',
        'Ы': 'I', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
        'ў': "o'", 'қ': 'q', 'ғ': "g'", 'ҳ': 'h',
        'Ў': "O'", 'Қ': 'Q', 'Ғ': "G'", 'Ҳ': 'H'
    }
    return ''.join(kiril_latin.get(c, c) for c in text)

async def analyze_check_image(image_path: str) -> dict:
    """Chek rasmini tahlil qilish (Smart Fallback)"""
    init_gemini()
    
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    
    prompt = """
Analyze this receipt image and extract:
1. All product names
2. Their quantities
3. Their prices
4. Total amount

Return ONLY a JSON object (no markdown, no backticks):
{
  "items": [
    {"name": "Product name in Latin alphabet", "quantity": number, "price": number}
  ],
  "total": number
}

Rules:
- Use ONLY Latin alphabet (a-z, A-Z)
- Ignore phone numbers, QR codes, dates
- If no clear items, return {"items": [], "total": 0}
"""
    
    max_attempts = len(GEMINI_MODELS)
    
    for attempt in range(max_attempts):
        try:
            model_name = GEMINI_MODELS[current_model_index]
            model = genai.GenerativeModel(model_name)
            
            response = model.generate_content([
                {"mime_type": "image/jpeg", "data": image_data},
                prompt
            ])
            
            text = response.text.strip()
            text = re.sub(r'```json\s*|\s*```', '', text).strip()
            
            data = json.loads(text)
            
            # Lotin'ga o'girish
            if "items" in data:
                for item in data["items"]:
                    if "name" in item:
                        item["name"] = transliterate_to_latin(item["name"])
            
            return data
            
        except Exception as e:
            error_str = str(e).lower()
            
            if "429" in error_str or "quota" in error_str or "resource_exhausted" in error_str:
                # Limit tugadi - keyingi modelga o'tish
                old_model = GEMINI_MODELS[current_model_index]
                new_model = get_next_model()
                print(f"⚠️ {old_model} limiti tugadi. {new_model} ga o'tildi.")
                continue
            else:
                # Boshqa xato
                print(f"AI xatosi: {e}")
                get_next_model()
                continue
    
    # Barcha modellar ishlamadi
    return {"items": [], "total": 0, "error": "Barcha AI modellar limiti tugagan. Iltimos, keyinroq qayta urinib ko'ring."}

async def transcribe_voice(voice_path: str) -> dict:
    """Ovozni matn va JSONga aylantirish (Smart Fallback)"""
    init_gemini()
    
    with open(voice_path, "rb") as f:
        audio_data = base64.standard_b64encode(f.read()).decode("utf-8")
    
    prompt = """
Convert this audio to text, then extract expense information.

Return ONLY a JSON object (no markdown, no backticks):
{
  "transcription": "full text in Latin alphabet",
  "amount": number (or 0 if not mentioned),
  "category": "category in Latin alphabet"
}

Rules:
- Use ONLY Latin alphabet
- If no amount mentioned, use 0
- Common categories: QURILISH, OZIQ-OVQAT, TRANSPORT, ALOQA, BOSHQA
"""
    
    max_attempts = len(GEMINI_MODELS)
    
    for attempt in range(max_attempts):
        try:
            model_name = GEMINI_MODELS[current_model_index]
            model = genai.GenerativeModel(model_name)
            
            response = model.generate_content([
                {"mime_type": "audio/ogg", "data": audio_data},
                prompt
            ])
            
            text = response.text.strip()
            text = re.sub(r'```json\s*|\s*```', '', text).strip()
            
            data = json.loads(text)
            
            # Lotin'ga o'girish
            if "transcription" in data:
                data["transcription"] = transliterate_to_latin(data["transcription"])
            if "category" in data:
                data["category"] = transliterate_to_latin(data["category"])
            
            return data
            
        except Exception as e:
            error_str = str(e).lower()
            
            if "429" in error_str or "quota" in error_str or "resource_exhausted" in error_str:
                old_model = GEMINI_MODELS[current_model_index]
                new_model = get_next_model()
                print(f"⚠️ {old_model} limiti tugadi. {new_model} ga o'tildi.")
                continue
            else:
                print(f"AI xatosi: {e}")
                get_next_model()
                continue
    
    return {"transcription": "", "amount": 0, "category": "BOSHQA", "error": "Barcha AI modellar limiti tugagan."}