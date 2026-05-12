import asyncio
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, GEMINI_API_KEY, ADMIN_PANEL_URL
from database import init_db, add_transaction, get_user_transactions
from ai_helper import analyze_check_with_ai, format_ai_check_summary, get_tashkent_time
from google import genai
from google.genai import types as genai_types

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)
client = genai.Client(api_key=GEMINI_API_KEY)

class AddExpense(StatesGroup):
    choosing_method = State()
    waiting_photo = State()
    confirming_photo = State()
    editing_photo = State()
    waiting_voice = State()
    confirming_voice = State()
    waiting_text_amount = State()
    waiting_text_description = State()

def main_menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="💸 CHIQIM")],[types.KeyboardButton(text="🔐 ADMIN")]],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"👋 Salom, {message.from_user.first_name}!\n\n"
        "💸 <b>Xarajatlar Nazorat Tizimi</b>\n\n"
        "Chek rasmi, ovozli xabar yoki matn orqali xarajat qoshing!",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@dp.message(F.text == "💸 CHIQIM")
async def btn_chiqim(message: types.Message, state: FSMContext):
    keyboard = [
        [types.KeyboardButton(text="📸 Chek rasmi")],
        [types.KeyboardButton(text="🎤 Ovozli xabar")],
        [types.KeyboardButton(text="✍️ Matn yozish")],
        [types.KeyboardButton(text="🔙 Bekor qilish")]
    ]
    await message.answer(
        "Qaysi usulda malumot yuborasiz?",
        reply_markup=types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    )
    await state.set_state(AddExpense.choosing_method)

@dp.message(AddExpense.choosing_method)
async def choose_method(message: types.Message, state: FSMContext):
    if message.text == "🔙 Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    
    keyboard = [[types.KeyboardButton(text="🔙 Bekor qilish")]]
    markup = types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    
    if message.text == "📸 Chek rasmi":
        await message.answer("📸 Chek rasmini yuboring:", reply_markup=markup)
        await state.set_state(AddExpense.waiting_photo)
    elif message.text == "🎤 Ovozli xabar":
        await message.answer(
            "🎤 Ovozli xabar yuboring:\n\n"
            "Masalan: 'Sement uchun uch yuz qirq besh ming som'",
            reply_markup=markup
        )
        await state.set_state(AddExpense.waiting_voice)
    elif message.text == "✍️ Matn yozish":
        await message.answer("💵 Summani kiriting:", reply_markup=markup)
        await state.set_state(AddExpense.waiting_text_amount)

@dp.message(AddExpense.waiting_photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    loading = await message.answer("🤖 AI chekni tahlil qilmoqda...")
    file_id = message.photo[-1].file_id
    file = await bot.get_file(file_id)
    file_path = f"check_{message.from_user.id}.jpg"
    await bot.download_file(file.file_path, file_path)
    
    data = analyze_check_with_ai(file_path)
    await loading.delete()
    
    if not data:
        await message.answer("❌ Chekni oqib bolmadi. Qaytadan yuboring.", reply_markup=main_menu())
        await state.clear()
        return
    
    if data.get("error") == "limit":
        await message.answer(
            "⏳ <b>AI limiti tugadi</b>\n\n"
            "Iltimos, bir necha soatdan keyin qayta urinib koring.\n"
            "Yoki ✍️ Matn yozish orqali xarajatni qoshing.",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    summary, items, total = format_ai_check_summary(data)
    await state.update_data(items=items, total=total, file_path=file_path, timestamp=data["timestamp"])
    
    keyboard = [
        [types.KeyboardButton(text="✅ Tasdiqlash")],
        [types.KeyboardButton(text="✏️ Tahrirlash")],
        [types.KeyboardButton(text="🔙 Bekor qilish")]
    ]
    await message.answer(
        summary + "\n\n<b>Tasdiqlaysizmi?</b>",
        reply_markup=types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True),
        parse_mode="HTML"
    )
    await state.set_state(AddExpense.confirming_photo)

@dp.message(AddExpense.confirming_photo)
async def confirm_photo(message: types.Message, state: FSMContext):
    if message.text == "🔙 Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    
    data = await state.get_data()
    
    if message.text == "✅ Tasdiqlash":
        for item in data["items"]:
            add_transaction(
                message.from_user.id,
                "CHIQIM",
                item["product"],
                item["amount"],
                f"Chek | {data['timestamp']}",
                data["timestamp"]
            )
        os.remove(data["file_path"])
        await message.answer("✅ <b>Xabaringiz tasdiqlandi!</b>", reply_markup=main_menu(), parse_mode="HTML")
        await state.clear()
    
    elif message.text == "✏️ Tahrirlash":
        await message.answer(
            "Tahrirlangan malumotni yozing:\n\n"
            "Format: Mahsulot - Summa\n"
            "Masalan:\nSement - 345000\nShifer - 200000"
        )
        await state.set_state(AddExpense.editing_photo)

@dp.message(AddExpense.editing_photo)
async def edit_photo(message: types.Message, state: FSMContext):
    items = []
    for line in message.text.strip().split("\n"):
        parts = line.split("-")
        if len(parts) == 2:
            try:
                items.append({
                    "product": parts[0].strip(),
                    "amount": float(parts[1].strip().replace(" ","").replace(",",""))
                })
            except:
                pass
    
    if not items:
        await message.answer("❌ Format notogri. Qaytadan:")
        return
    
    data = await state.get_data()
    timestamp = get_tashkent_time()
    
    for item in items:
        add_transaction(
            message.from_user.id,
            "CHIQIM",
            item["product"],
            item["amount"],
            f"Tahrirlangan | {timestamp}",
            timestamp
        )
    
    os.remove(data["file_path"])
    await message.answer("✅ <b>Xabaringiz tasdiqlandi!</b>", reply_markup=main_menu(), parse_mode="HTML")
    await state.clear()

@dp.message(AddExpense.waiting_voice, F.voice)
async def process_voice(message: types.Message, state: FSMContext):
    loading = await message.answer("🤖 AI ovozni tahlil qilmoqda...")
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    voice_path = f"voice_{message.from_user.id}.ogg"
    await bot.download_file(file.file_path, voice_path)
    
    try:
        with open(voice_path, "rb") as f:
            audio_data = f.read()
        
        prompt = """
Bu ovozli xabarda xarajat haqida gap boradi.

VAZIFA: Ovozdan mahsulot/xizmat nomi va summani ajratib JSON qaytaring.

QOIDALAR:
1. Summani raqamga aylantiring (masalan: "uch yuz ming" -> 300000)
2. Barcha matnni LOTIN ALIFBOSIDA yozing
3. FORMAT: {"items": [{"product": "...", "amount": 123456}], "total": 123456}

Faqat JSON, LOTIN ALIFBOSIDA!
"""
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[genai_types.Content(role="user", parts=[
                genai_types.Part.from_bytes(data=audio_data, mime_type="audio/ogg"),
                genai_types.Part.from_text(text=prompt)
            ])]
        )
        
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        import json
        data = json.loads(text)
        data["timestamp"] = get_tashkent_time()
        
        os.remove(voice_path)
        await loading.delete()
        
        summary, items, total = format_ai_check_summary(data)
        await state.update_data(items=items, total=total, timestamp=data["timestamp"])
        
        keyboard = [
            [types.KeyboardButton(text="✅ Tasdiqlash")],
            [types.KeyboardButton(text="🔙 Bekor qilish")]
        ]
        await message.answer(
            summary + "\n\n<b>Tasdiqlaysizmi?</b>",
            reply_markup=types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True),
            parse_mode="HTML"
        )
        await state.set_state(AddExpense.confirming_voice)
    
    except Exception as e:
        if os.path.exists(voice_path):
            os.remove(voice_path)
        await loading.delete()
        error_str = str(e)
        if "RESOURCE_EXHAUSTED" in error_str or "429" in error_str:
            await message.answer(
                "⏳ <b>AI limiti tugadi</b>\n\n"
                "Iltimos, bir necha soatdan keyin qayta urinib koring.\n"
                "Yoki ✍️ Matn yozish orqali xarajatni qoshing.",
                reply_markup=main_menu(),
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "❌ Ovozni tahlil qilib bolmadi. Qaytadan yuboring.",
                reply_markup=main_menu()
            )
        await state.clear()

@dp.message(AddExpense.confirming_voice)
async def confirm_voice(message: types.Message, state: FSMContext):
    if message.text == "🔙 Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    
    if message.text == "✅ Tasdiqlash":
        data = await state.get_data()
        for item in data["items"]:
            add_transaction(
                message.from_user.id,
                "CHIQIM",
                item["product"],
                item["amount"],
                f"Ovozli xabar | {data['timestamp']}",
                data["timestamp"]
            )
        await message.answer("✅ <b>Xabaringiz tasdiqlandi!</b>", reply_markup=main_menu(), parse_mode="HTML")
        await state.clear()

@dp.message(AddExpense.waiting_text_amount)
async def text_amount(message: types.Message, state: FSMContext):
    if message.text == "🔙 Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=main_menu())
        return
    
    try:
        amount = float(message.text.replace(" ","").replace(",",""))
        await state.update_data(amount=amount)
        await message.answer("📝 Nima uchun? (mahsulot/xizmat nomi)")
        await state.set_state(AddExpense.waiting_text_description)
    except:
        await message.answer("❌ Faqat raqam. Qaytadan:")

@dp.message(AddExpense.waiting_text_description)
async def text_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    timestamp = get_tashkent_time()
    add_transaction(
        message.from_user.id,
        "CHIQIM",
        message.text,
        data["amount"],
        f"Qolda kiritilgan | {timestamp}",
        timestamp
    )
    await message.answer("✅ <b>Xabaringiz tasdiqlandi!</b>", reply_markup=main_menu(), parse_mode="HTML")
    await state.clear()

@dp.message(F.text == "🔐 ADMIN")
async def btn_admin(message: types.Message):
    await message.answer(
        f"🌐 <b>Admin Panel</b>\n\n"
        f"Quyidagi havola orqali admin panelga kiring:\n\n"
        f"{ADMIN_PANEL_URL}\n\n"
        f"📊 Tezkor hisobot: /report",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@dp.message(Command("report"))
async def cmd_report(message: types.Message):
    trans = get_user_transactions(message.from_user.id)
    
    if not trans:
        await message.answer("📭 Xarajatlar yoq.")
        return
    
    text = "📊 <b>HISOBOTLAR</b> (oxirgi 20 ta)\n\n"
    total = 0
    for t in trans[:20]:
        text += f"🕒 {t[6]}\n📦 {t[3]}: {t[4]:,.0f} som\n{'—'*20}\n"
        total += t[4]
    
    text += f"\n💰 <b>Jami: {total:,.0f} som</b>\n\n"
    text += f"🌐 To'liq hisobot: {ADMIN_PANEL_URL}"
    await message.answer(text, parse_mode="HTML")

async def main():
    init_db()
    print("=" * 50)
    print("🤖 BOT ISHGA TUSHDI!")
    print("=" * 50)
    print("\n✅ Chek rasmi + AI tahlil")
    print("✅ Ovozli xabar + AI tahlil")
    print("✅ Matn orqali kiritish")
    print("✅ Admin panel (parolsiz)")
    print(f"\n🌐 Veb panel: {ADMIN_PANEL_URL}\n")
    print("=" * 50)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


