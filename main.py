import asyncio
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import os
from datetime import datetime
import pytz
import calendar

from config import BOT_TOKEN, ADMIN_PANEL_URL, DB_PATH
from database import init_db, add_transaction, get_transactions, get_transactions_by_date, get_monthly_stats
from ai_helper import analyze_check_image, transcribe_voice
from currency_api import get_usd_rate, format_currency
from datetime import datetime, timedelta  # ← BU QO'SHILDI

# Bot setup
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# FSM States
class ExpenseStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_description = State()
    waiting_for_confirmation = State()

# Timezone
TZ = pytz.timezone("Asia/Tashkent")

# Asosiy menyu
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💸 CHIQIM")],
            [KeyboardButton(text="📊 HISOBOTLAR")]
        ],
        resize_keyboard=True
    )

# Chiqim turlari
def get_expense_types():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📸 Chek rasmi"), KeyboardButton(text="🎤 Ovozli xabar")],
            [KeyboardButton(text="✍️ Matn yozish")],
            [KeyboardButton(text="🔙 Orqaga")]
        ],
        resize_keyboard=True
    )

# Hisobotlar menyusi
def get_reports_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Oylar bo'yicha")],
            [KeyboardButton(text="📥 Excel yuklash")],
            [KeyboardButton(text="🔙 Orqaga")]
        ],
        resize_keyboard=True
    )

# /start
@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Assalomu alaykum, {message.from_user.first_name}!\n\n"
        "🤖 BOT ISHGA TUSHDI!\n\n"
        "✅ Chek rasmi + AI tahlil\n"
        "✅ Ovozli xabar + AI tahlil\n"
        "✅ Matn orqali kiritish\n"
        "✅ Hisobotlar (oylar, kunlar, kunlik)\n"
        "✅ Excel export (hafta/oy/yil)\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=get_main_menu()
    )

# 💸 CHIQIM
@router.message(F.text == "💸 CHIQIM")
async def show_expense_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Qaysi usulda xarajat qo'shasiz?",
        reply_markup=get_expense_types()
    )

# 📸 Chek rasmi
@router.message(F.text == "📸 Chek rasmi")
async def ask_for_check_image(message: types.Message):
    await message.answer("📸 Chek rasmini yuboring:")

@router.message(F.photo)
async def handle_check_image(message: types.Message):
    status_msg = await message.answer("⏳ AI tahlil qilyapti...")
    
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = f"check_{message.from_user.id}.jpg"
    await bot.download_file(file.file_path, file_path)
    
    result = await analyze_check_image(file_path)
    
    if "error" in result:
        await status_msg.edit_text(f"❌ Xato: {result['error']}")
        return
    
    if not result.get("items"):
        await status_msg.edit_text("❌ Chekdan ma'lumot tanib olinmadi. Iltimos, matn orqali kiriting.")
        return
    
    # Tahlil natijasi
    items_text = "\n".join([f"{i+1}. {item['name']}: {format_currency(item['price'])}" for i, item in enumerate(result["items"])])
    
    await status_msg.edit_text(
        f"📋 AI tahlil:\n\n{items_text}\n\n"
        f"💰 Jami: {format_currency(result['total'])}\n\n"
        "Tasdiqlaysizmi?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha", callback_data=f"confirm_check:{result['total']}"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel")
            ]
        ])
    )
    
    os.remove(file_path)

@router.callback_query(F.data.startswith("confirm_check:"))
async def confirm_check(callback: types.CallbackQuery):
    amount = int(callback.data.split(":")[1])
    
    now = datetime.now(TZ)
    add_transaction(
        user_id=callback.from_user.id,
        trans_type="CHIQIM",
        category="AI Tahlil",
        amount=amount,
        description="Chek rasmi orqali",
        date=now.strftime("%Y-%m-%d %H:%M:%S")
    )
    
    await callback.message.edit_text(
        f"✅ Xarajat saqlandi!\n\n"
        f"💵 Summa: {format_currency(amount)}\n"
        f"📅 Sana: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"🌐 To'liq hisobot: {ADMIN_PANEL_URL}"
    )

# 🎤 Ovozli xabar
@router.message(F.text == "🎤 Ovozli xabar")
async def ask_for_voice(message: types.Message):
    await message.answer("🎤 Ovozli xabar yuboring:")

@router.message(F.voice)
async def handle_voice(message: types.Message):
    status_msg = await message.answer("⏳ AI ovozni taniyapti...")
    
    voice = message.voice
    file = await bot.get_file(voice.file_id)
    file_path = f"voice_{message.from_user.id}.ogg"
    await bot.download_file(file.file_path, file_path)
    
    result = await transcribe_voice(file_path)
    
    if "error" in result:
        await status_msg.edit_text(f"❌ Xato: {result['error']}")
        return
    
    if result["amount"] == 0:
        await status_msg.edit_text(
            f"📝 Matn: {result['transcription']}\n\n"
            "❌ Summa aniqlanmadi. Iltimos, matn orqali kiriting."
        )
        return
    
    await status_msg.edit_text(
        f"📝 Matn: {result['transcription']}\n"
        f"💰 Summa: {format_currency(result['amount'])}\n"
        f"📦 Kategoriya: {result['category']}\n\n"
        "Tasdiqlaysizmi?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha", callback_data=f"confirm_voice:{result['amount']}:{result['category']}"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel")
            ]
        ])
    )
    
    os.remove(file_path)

@router.callback_query(F.data.startswith("confirm_voice:"))
async def confirm_voice(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    amount = int(parts[1])
    category = parts[2]
    
    now = datetime.now(TZ)
    add_transaction(
        user_id=callback.from_user.id,
        trans_type="CHIQIM",
        category=category,
        amount=amount,
        description="Ovozli xabar orqali",
        date=now.strftime("%Y-%m-%d %H:%M:%S")
    )
    
    await callback.message.edit_text(
        f"✅ Xarajat saqlandi!\n\n"
        f"💵 Summa: {format_currency(amount)}\n"
        f"📦 Kategoriya: {category}\n"
        f"📅 Sana: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    )

# ✍️ Matn yozish
@router.message(F.text == "✍️ Matn yozish")
async def ask_for_amount(message: types.Message, state: FSMContext):
    await message.answer("💵 Summani kiriting:")
    await state.set_state(ExpenseStates.waiting_for_amount)

@router.message(ExpenseStates.waiting_for_amount)
async def get_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text.replace(",", "").replace(" ", ""))
        await state.update_data(amount=amount)
        await message.answer("📝 Nima uchun? (mahsulot/xizmat nomi):")
        await state.set_state(ExpenseStates.waiting_for_description)
    except:
        await message.answer("❌ Noto'g'ri format. Faqat raqam kiriting:")

@router.message(ExpenseStates.waiting_for_description)
async def get_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    amount = data["amount"]
    description = message.text
    
    await message.answer(
        f"💰 Summa: {format_currency(amount)}\n"
        f"📝 Izoh: {description}\n\n"
        "Tasdiqlaysizmi?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha", callback_data=f"confirm_manual:{amount}:{description}"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel")
            ]
        ])
    )

@router.callback_query(F.data.startswith("confirm_manual:"))
async def confirm_manual(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":", 2)
    amount = int(parts[1])
    description = parts[2]
    
    now = datetime.now(TZ)
    add_transaction(
        user_id=callback.from_user.id,
        trans_type="CHIQIM",
        category="Matn",
        amount=amount,
        description=description,
        date=now.strftime("%Y-%m-%d %H:%M:%S")
    )
    
    await callback.message.edit_text(
        f"✅ Xarajat saqlandi!\n\n"
        f"💵 Summa: {format_currency(amount)}\n"
        f"📝 Izoh: {description}\n"
        f"📅 Sana: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    await state.clear()

# 📊 HISOBOTLAR
@router.message(F.text == "📊 HISOBOTLAR")
async def show_reports_menu(message: types.Message):
    await message.answer("📊 Hisobotlar bo'limi:", reply_markup=get_reports_menu())

# 📅 Oylar bo'yicha
@router.message(F.text == "📅 Oylar bo'yicha")
async def show_months(message: types.Message):
    year = datetime.now(TZ).year
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣ Yanvar", callback_data=f"month:{year}:01"),
            InlineKeyboardButton(text="2️⃣ Fevral", callback_data=f"month:{year}:02"),
            InlineKeyboardButton(text="3️⃣ Mart", callback_data=f"month:{year}:03")
        ],
        [
            InlineKeyboardButton(text="4️⃣ Aprel", callback_data=f"month:{year}:04"),
            InlineKeyboardButton(text="5️⃣ May", callback_data=f"month:{year}:05"),
            InlineKeyboardButton(text="6️⃣ Iyun", callback_data=f"month:{year}:06")
        ],
        [
            InlineKeyboardButton(text="7️⃣ Iyul", callback_data=f"month:{year}:07"),
            InlineKeyboardButton(text="8️⃣ Avgust", callback_data=f"month:{year}:08"),
            InlineKeyboardButton(text="9️⃣ Sentyabr", callback_data=f"month:{year}:09")
        ],
        [
            InlineKeyboardButton(text="🔟 Oktyabr", callback_data=f"month:{year}:10"),
            InlineKeyboardButton(text="1️⃣1️⃣ Noyabr", callback_data=f"month:{year}:11"),
            InlineKeyboardButton(text="1️⃣2️⃣ Dekabr", callback_data=f"month:{year}:12")
        ]
    ])
    await message.answer(f"📅 {year}-yil. Oyni tanlang:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("month:"))
async def show_days(callback: types.CallbackQuery):
    _, year, month = callback.data.split(":")
    year, month = int(year), int(month)
    
    # Oy nomi
    month_names = ["", "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun", 
                   "Iyul", "Avgust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr"]
    
    # Kunlar soni
    _, days_in_month = calendar.monthrange(year, month)
    
    # Inline keyboard (5 kun bir qatorda)
    keyboard = []
    row = []
    for day in range(1, days_in_month + 1):
        row.append(InlineKeyboardButton(text=str(day), callback_data=f"day:{year}:{month}:{day}"))
        if len(row) == 5:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_months")])
    
    await callback.message.edit_text(
        f"📅 {month_names[month]} {year}\n\nKunni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data.startswith("day:"))
async def show_day_report(callback: types.CallbackQuery):
    _, year, month, day = callback.data.split(":")
    date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    transactions = get_transactions_by_date(date_str)
    
    if not transactions:
        await callback.message.edit_text(
            f"📅 {date_str}\n\n❌ Bu kunda xarajat yo'q.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"month:{year}:{month}")]
            ])
        )
        return
    
    total = sum(t["amount"] for t in transactions)
    report = f"📅 {date_str}\n\n"
    
    for i, t in enumerate(transactions, 1):
        report += f"{i}. {t['category']}: {format_currency(t['amount'])}\n   {t['description']}\n   🕐 {t['date']}\n\n"
    
    report += f"💰 JAMI: {format_currency(total)}"
    
    await callback.message.edit_text(
        report,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"month:{year}:{month}")]
        ])
    )

@router.callback_query(F.data == "back_to_months")
async def back_to_months(callback: types.CallbackQuery):
    year = datetime.now(TZ).year
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣ Yanvar", callback_data=f"month:{year}:01"),
            InlineKeyboardButton(text="2️⃣ Fevral", callback_data=f"month:{year}:02"),
            InlineKeyboardButton(text="3️⃣ Mart", callback_data=f"month:{year}:03")
        ],
        [
            InlineKeyboardButton(text="4️⃣ Aprel", callback_data=f"month:{year}:04"),
            InlineKeyboardButton(text="5️⃣ May", callback_data=f"month:{year}:05"),
            InlineKeyboardButton(text="6️⃣ Iyun", callback_data=f"month:{year}:06")
        ],
        [
            InlineKeyboardButton(text="7️⃣ Iyul", callback_data=f"month:{year}:07"),
            InlineKeyboardButton(text="8️⃣ Avgust", callback_data=f"month:{year}:08"),
            InlineKeyboardButton(text="9️⃣ Sentyabr", callback_data=f"month:{year}:09")
        ],
        [
            InlineKeyboardButton(text="🔟 Oktyabr", callback_data=f"month:{year}:10"),
            InlineKeyboardButton(text="1️⃣1️⃣ Noyabr", callback_data=f"month:{year}:11"),
            InlineKeyboardButton(text="1️⃣2️⃣ Dekabr", callback_data=f"month:{year}:12")
        ]
    ])
    await callback.message.edit_text(f"📅 {year}-yil. Oyni tanlang:", reply_markup=keyboard)

# 📥 Excel yuklash
@router.message(F.text == "📥 Excel yuklash")
async def ask_excel_period(message: types.Message):
    await message.answer(
        "📥 Qaysi davr uchun Excel hisobotni yuklamoqchisiz?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📆 Haftalik", callback_data="excel:week")],
            [InlineKeyboardButton(text="📅 Oylik", callback_data="excel:month")],
            [InlineKeyboardButton(text="📊 Yillik", callback_data="excel:year")]
        ])
    )

@router.callback_query(F.data.startswith("excel:"))
async def generate_excel(callback: types.CallbackQuery):
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    import io
    
    period = callback.data.split(":")[1]
    
    now = datetime.now(TZ)
    
    if period == "week":
        start_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        filename = f"haftalik_{now.strftime('%Y%m%d')}.xlsx"
    elif period == "month":
        start_date = now.replace(day=1).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        filename = f"oylik_{now.strftime('%Y%m')}.xlsx"
    else:  # year
        start_date = now.replace(month=1, day=1).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        filename = f"yillik_{now.year}.xlsx"
    
    transactions = get_transactions_by_date(start_date, end_date)
    
    if not transactions:
        await callback.message.answer("❌ Bu davrda xarajat yo'q.")
        return
    
    # Excel yaratish
    wb = Workbook()
    ws = wb.active
    ws.title = "Xarajatlar"
    
    # Header
    header_fill = PatternFill(start_color="667eea", end_color="667eea", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    
    headers = ["№", "Sana", "Kategoriya", "Summa (som)", "Izoh"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    
    # Ma'lumotlar
    total = 0
    for idx, t in enumerate(transactions, 2):
        ws.cell(row=idx, column=1, value=idx-1)
        ws.cell(row=idx, column=2, value=t["date"])
        ws.cell(row=idx, column=3, value=t["category"])
        ws.cell(row=idx, column=4, value=t["amount"])
        ws.cell(row=idx, column=5, value=t["description"])
        total += t["amount"]
    
    # Jami
    ws.cell(row=len(transactions)+2, column=3, value="JAMI:").font = Font(bold=True)
    ws.cell(row=len(transactions)+2, column=4, value=total).font = Font(bold=True, size=14)
    
    # Column widths
    for col in range(1, 6):
        ws.column_dimensions[chr(64+col)].width = 20
    
    # Save
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    await callback.message.answer_document(
        types.BufferedInputFile(output.read(), filename=filename),
        caption=f"📥 {period.capitalize()} hisobot\n💰 Jami: {format_currency(total)}"
    )

# 🔙 Orqaga
@router.message(F.text == "🔙 Orqaga")
async def go_back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menyu:", reply_markup=get_main_menu())

# ❌ Bekor qilish
@router.callback_query(F.data == "cancel")
async def cancel_action(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Bekor qilindi.")

# Ishga tushirish
async def main():
    print("=" * 50)
    print("✅ Baza tayyor!")
    print("=" * 50)
    print("🤖 BOT ISHGA TUSHDI!")
    print("=" * 50)
    print("\n✅ Chek rasmi + AI tahlil")
    print("✅ Ovozli xabar + AI tahlil")
    print("✅ Matn orqali kiritish")
    print("✅ Hisobotlar (oylar, kunlar, kunlik)")
    print("✅ Excel export (hafta/oy/yil)")
    print("✅ Smart AI Fallback (10+ model)\n")
    print("=" * 50)
    
    init_db()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())