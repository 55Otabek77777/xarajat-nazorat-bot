import google.generativeai as genai
from config import GEMINI_API_KEYS, GEMINI_MODELS, ANTHROPIC_API_KEY, CLAUDE_MODEL
import base64
import json
import re

current_key_index = 0
current_model_index = 0

def get_next_model():
    global current_model_index
    current_model_index = (current_model_index + 1) % len(GEMINI_MODELS)
    return GEMINI_MODELS[current_model_index]

def init_gemini():
    genai.configure(api_key=GEMINI_API_KEYS[current_key_index])

def transliterate_to_latin(text):
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
        'Ы': 'I', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    return ''.join(kiril_latin.get(c, c) for c in text)

async def try_claude_vision(image_base64: str, prompt: str) -> dict:
    """Claude Haiku Vision (PULLIK - ishonchli)"""
    if not ANTHROPIC_API_KEY:
        print("⚠️ ANTHROPIC_API_KEY topilmadi")
        return None
    
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        )
        
        text = message.content[0].text.strip()
        text = re.sub(r'```json\s*|\s*```', '', text).strip()
        
        data = json.loads(text)
        
        if "items" in data:
            for item in data["items"]:
                if "name" in item:
                    item["name"] = transliterate_to_latin(item["name"])
        
        return data
        
    except Exception as e:
        print(f"❌ Claude xatosi: {e}")
        return None

async def analyze_check_image(image_path: str) -> dict:
    """
    RASM TAHLIL QILISH:
    1. Claude Haiku (PULLIK - ishonchli)
    2. Gemini (10 model - TEKIN)
    3. Matn orqali kiriting
    """
    
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
    
    # 1️⃣ CLAUDE HAIKU (BIRINCHI - ishonchli)
    print("💰 Claude Haiku ishlatilmoqda...")
    claude_result = await try_claude_vision(image_data, prompt)
    if claude_result:
        print("✅ Claude Haiku muvaffaqiyatli!")
        return claude_result
    
    # 2️⃣ GEMINI modellar (RESERVE)
    print("⚠️ Claude ishlamadi. Gemini ishlatilmoqda...")
    init_gemini()
    
    for attempt in range(len(GEMINI_MODELS)):
        try:
            model_name = GEMINI_MODELS[current_model_index]
            print(f"🔄 Sinash: {model_name}")
            
            model = genai.GenerativeModel(model_name)
            
            response = model.generate_content([
                {"mime_type": "image/jpeg", "data": image_data},
                prompt
            ])
            
            text = response.text.strip()
            text = re.sub(r'```json\s*|\s*```', '', text).strip()
            
            data = json.loads(text)
            
            if "items" in data:
                for item in data["items"]:
                    if "name" in item:
                        item["name"] = transliterate_to_latin(item["name"])
            
            print(f"✅ Gemini {model_name} muvaffaqiyatli!")
            return data
            
        except Exception as e:
            error_str = str(e).lower()
            old_model = GEMINI_MODELS[current_model_index]
            new_model = get_next_model()
            
            print(f"❌ {old_model} xatosi: {str(e)[:100]}")
            print(f"🔄 Keyingi model: {new_model}")
            continue
    
    # 3️⃣ Hech biri ishlamadi
    print("❌ Barcha AI modellar ishlamadi!")
    return {
        "items": [],
        "total": 0,
        "error": "AI tahlil qila olmadi. Iltimos, xarajatni matn orqali kiriting."
    }

async def transcribe_voice(voice_path: str) -> dict:
    """
    OVOZ TANISH:
    1. Gemini (10 model - TEKIN)
    2. Matn orqali kiriting
    """
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
    
    for attempt in range(len(GEMINI_MODELS)):
        try:
            model_name = GEMINI_MODELS[current_model_index]
            print(f"🔄 Ovoz tanish: {model_name}")
            
            model = genai.GenerativeModel(model_name)
            
            response = model.generate_content([
                {"mime_type": "audio/ogg", "data": audio_data},
                prompt
            ])
            
            text = response.text.strip()
            text = re.sub(r'```json\s*|\s*```', '', text).strip()
            
            data = json.loads(text)
            
            if "transcription" in data:
                data["transcription"] = transliterate_to_latin(data["transcription"])
            if "category" in data:
                data["category"] = transliterate_to_latin(data["category"])
            
            print(f"✅ Gemini {model_name} ovozni tanidi!")
            return data
            
        except Exception as e:
            old_model = GEMINI_MODELS[current_model_index]
            new_model = get_next_model()
            
            print(f"❌ {old_model} xatosi: {str(e)[:100]}")
            print(f"🔄 Keyingi model: {new_model}")
            continue
    
    print("❌ Barcha Gemini modellar ishlamadi!")
    return {
        "transcription": "",
        "amount": 0,
        "category": "BOSHQA",
        "error": "AI ovozni taniy olmadi. Iltimos, xarajatni matn orqali kiriting."
    }