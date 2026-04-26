import os
import asyncio
import sqlite3
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramRetryAfter

# 🔥 Құпия мәліметтерді оқу
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ==========================================
# 🌐 ПРОКСИДІ ТЕК БОТТЫҢ ӨЗІНЕ ҒАНА ҚОСУ
# ==========================================
if "PYTHONANYWHERE_SITE" in os.environ:
    session = AiohttpSession(proxy="http://proxy.server:3128")
    bot = Bot(token=BOT_TOKEN, session=session)
else:
    bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

# Уақытша жад
user_states = {}
user_history = {}
HISTORY_LIMIT = 20

CATEGORY_MAP = {
    "алгебра": "🔢 Алгебра", "мат": "🔢 Алгебра",
    "геометрия": "📐 Геометрия", "геом": "📐 Геометрия",
    "тригонометрия": "🔄 Тригонометрия", "информатика": "💻 Информатика", "инфо": "💻 Информатика"
}

# ==========================================
# 1. ДЕРЕКҚОР ЖӘНЕ ЛОГИКА
# ==========================================
def init_db():
    conn = sqlite3.connect('unt_bot.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS formulas (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, formula_text TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, join_date DATETIME DEFAULT CURRENT_TIMESTAMP)')

    cursor.execute("UPDATE formulas SET category = '📐 Геометрия' WHERE category LIKE '%Геометрия%'")
    cursor.execute("UPDATE formulas SET category = '🔢 Алгебра' WHERE category LIKE '%Алгебра%'")
    cursor.execute("UPDATE formulas SET category = '🔄 Тригонометрия' WHERE category LIKE '%Тригонометрия%'")
    cursor.execute("UPDATE formulas SET category = '💻 Информатика' WHERE category LIKE '%Информатика%'")
    cursor.execute('''DELETE FROM formulas WHERE id NOT IN (SELECT MIN(id) FROM formulas GROUP BY category, LOWER(REPLACE(formula_text, ' ', '')))''')
    conn.commit()
    conn.close()

def get_smart_formula(user_id, category):
    conn = sqlite3.connect('unt_bot.db')
    cursor = conn.cursor()
    seen_ids = user_history.get(user_id, [])

    if seen_ids:
        placeholders = ', '.join('?' for _ in seen_ids)
        query = f'SELECT id, formula_text FROM formulas WHERE category = ? AND id NOT IN ({placeholders}) ORDER BY RANDOM() LIMIT 1'
        cursor.execute(query, [category] + seen_ids)
    else:
        cursor.execute('SELECT id, formula_text FROM formulas WHERE category = ? ORDER BY RANDOM() LIMIT 1', (category,))

    result = cursor.fetchone()
    if not result:
        user_history[user_id] = []
        cursor.execute('SELECT id, formula_text FROM formulas WHERE category = ? ORDER BY RANDOM() LIMIT 1', (category,))
        result = cursor.fetchone()

    conn.close()
    if result:
        f_id, f_text = result
        if user_id not in user_history: user_history[user_id] = []
        user_history[user_id].append(f_id)
        if len(user_history[user_id]) > HISTORY_LIMIT: user_history[user_id].pop(0)
        return f_text
    return "Бұл бөлімде әзірше формула жоқ 😔"

# ==========================================
# 2. ПЕРНЕТАҚТА (ДИЗАЙН)
# ==========================================
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔢 Алгебра"), KeyboardButton(text="📐 Геометрия")],
        [KeyboardButton(text="🔄 Тригонометрия"), KeyboardButton(text="💻 Информатика")],
        [KeyboardButton(text="🔍 Іздеу"), KeyboardButton(text="🌟 Күннің формуласы")],
        [KeyboardButton(text="✍️ Кері байланыс"), KeyboardButton(text="ℹ️ Бот туралы")]
    ],
    resize_keyboard=True,
    input_field_placeholder="👇 Бөлімді таңдаңыз немесе іздеңіз..."
)

about_inline_btn = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="👨‍💻 Автормен байланыс", url="https://t.me/bekzat_dev_pro")],
        [InlineKeyboardButton(text="💳 Авторға қолдау (Kaspi)", callback_data="donate_info")]
    ]
)

# ==========================================
# 🎨 РЕСМИ МЕНЮ ҚОСУ
# ==========================================
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Ботты қайта іске қосу"),
        BotCommand(command="help", description="🆘 Ботты қалай қолданамын?"),
        BotCommand(command="report", description="✍️ Қате туралы хабарлау")
    ]
    await bot.set_my_commands(commands)

# ==========================================
# 3. ҚОЛДАНУШЫ ИНТЕРФЕЙСІ
# ==========================================
@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    conn = sqlite3.connect('unt_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (message.from_user.id,))
    conn.commit()
    conn.close()

    welcome_text = (
        "🎓 <b>ҰБТ Көмекшісіне қош келдіңіз!</b>\n\n"
        "Бұл бот — сіздің математика мен информатикадан сенімді серігіңіз.\n\n"
        "💡 <i>Төмендегі мәзірден пәнді таңдаңыз немесе «🔍 Іздеу» арқылы керекті формуланы жазыңыз.</i>"
    )

    await message.answer(
        text=welcome_text,
        reply_markup=main_keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "donate_info")
async def show_donate_info(callback: types.CallbackQuery):
    await callback.message.answer(
        "☕ **Авторға қолдау көрсеткіңіз келе ме?**\n\n"
        "💳 **Kaspi:** `+7 705 297 32 25`\n\n"
        "Сіздің қолдауыңыз ботты дамытуға жұмсалады. Рақмет! ❤️"
    )
    await callback.answer()

@dp.message(lambda message: not message.text.startswith('/'))
async def handle_text(message: types.Message):
    uid = message.from_user.id
    text = message.text

    # 1. Пән батырмалары (Флешкарта)
    if text in ["🔢 Алгебра", "📐 Геометрия", "🔄 Тригонометрия", "💻 Информатика"]:
        formula = get_smart_formula(uid, text)
        if "Бұл бөлімде әзірше" in formula:
            await message.answer(formula)
            return

        if ":" in formula:
            title, math_part = formula.split(":", 1)
            response_text = (
                f"📚 <b>Пән:</b> {text}\n"
                f"🏷 <b>Тақырып:</b> <i>{title.strip()}</i>\n\n"
                f"👇 <b>Формула:</b>\n"
                f"<tg-spoiler>{math_part.strip()}</tg-spoiler>\n\n"
                f"<i>💡 Өзіңізді тексеру үшін жасырын мәтінді басыңыз!</i>"
            )
        else:
            response_text = (
                f"📚 <b>Пән:</b> {text}\n\n"
                f"👇 <b>Формула:</b>\n"
                f"<tg-spoiler>{formula}</tg-spoiler>\n\n"
                f"<i>💡 Өзіңізді тексеру үшін жасырын мәтінді басыңыз!</i>"
            )
        await message.answer(response_text, parse_mode="HTML")
        return

    # 2. Күннің формуласы
    if text == "🌟 Күннің формуласы":
        conn = sqlite3.connect('unt_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT category, formula_text FROM formulas ORDER BY RANDOM() LIMIT 1')
        result = cursor.fetchone()
        conn.close()

        if result:
            cat, f_text = result
            if ":" in f_text:
                title, math_part = f_text.split(":", 1)
                daily_text = (
                    f"📅 <b>БҮГІНГІ ТАҢДАЛҒАН ФОРМУЛА</b>\n\n"
                    f"🔹 <b>Пән:</b> {cat}\n"
                    f"📌 <b>Тақырып:</b> {title.strip()}\n\n"
                    f"🧠 <b>Жаттап алыңыз:</b>\n"
                    f"<code>{math_part.strip()}</code>"
                )
            else:
                daily_text = f"📅 <b>БҮГІНГІ ФОРМУЛА</b>\n\n🔹 {cat}\n\n<code>{f_text}</code>"
            await message.answer(daily_text, parse_mode="HTML")
        else:
            await message.answer("База бос 😔")
        return

    # 3. Бот туралы
    if text == "ℹ️ Бот туралы":
        about_text = (
            "🤖 <b>ҰБТ Көмекшісі</b>\n\n"
            "Бұл бот оқушыларға ҰБТ-ға дайындалуға көмектесу мақсатында жасалған.\n"
            "Егер бот сізге пайдалы болса, авторға қолдау көрсете аласыз немесе жеке байланысқа шыға аласыз 👇"
        )
        await message.answer(about_text, reply_markup=about_inline_btn, parse_mode="HTML")
        return

    # 4. Кері байланыс
    if text == "✍️ Кері байланыс":
        user_states[uid] = 'waiting_feedback'
        await message.answer("📩 **Қате немесе ұсынысыңызды жазып жіберіңіз:**\n(Мен оны авторға тікелей жеткіземін)")
        return

    if user_states.get(uid) == 'waiting_feedback':
        await bot.send_message(ADMIN_ID, f"📩 **ЖАҢА ХАТ!**\n👤 {message.from_user.full_name}\n🆔 `{uid}`\n📝 {text}")
        user_states[uid] = None
        await message.answer("✅ Рақмет! Хабарламаңыз авторға жіберілді.")
        return

    # 5. Іздеу
    if text == "🔍 Іздеу":
        await message.answer("🔍 Іздегіңіз келетін сөзді жазыңыз (мысалы: Пифагор):")
        return

    # 6. Ақылды іздеу
    query = text.lower().strip()
    if len(query) < 2: return

    conn = sqlite3.connect('unt_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT category, formula_text FROM formulas')
    all_f = cursor.fetchall()
    conn.close()

    matches = []
    for cat, f_text in all_f:
        if any(word[:4] in f_text.lower() for word in query.split()):
            matches.append((cat, f_text))

    if matches:
        res = "🔍 **Табылды:**\n\n"
        for cat, f_text in matches[:5]: res += f"🔹 {cat}: `{f_text}`\n\n"
        await message.answer(res)
    else:
        await message.answer("😔 Табылмады. Басқаша жазып көріңіз.")

# ==========================================
# 4. АДМИН ПАНЕЛЬ
# ==========================================
@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect('unt_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM formulas')
    f_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM users')
    u_count = cursor.fetchone()[0]
    conn.close()
    await message.answer(f"📊 **Статистика:**\n\n👥 Пайдаланушылар: `{u_count}`\n📚 Формулалар: `{f_count}`")

@dp.message(Command("add"))
async def add_new_formula(message: types.Message):
    if message.from_user.id != ADMIN_ID: return

    raw_text = message.text.replace("/add", "").strip()

    if not raw_text:
        await message.answer("❌ Үлгі:\n`/add \nмат - a+b\nгеом - c=a+b`")
        return

    lines = raw_text.split('\n')
    added_count = 0
    skipped_count = 0
    errors = 0

    conn = sqlite3.connect('unt_bot.db')
    cursor = conn.cursor()

    for line in lines:
        line = line.strip()
        if not line:
            continue 

        try:
            cat_input, formula = line.split(" - ", 1)
            clean_cat = cat_input.strip().lower().replace(":", "")
            category = CATEGORY_MAP.get(clean_cat, clean_cat.capitalize())
            formula = formula.strip()
            norm_f = formula.replace(" ", "").lower()

            cursor.execute('SELECT formula_text FROM formulas WHERE category = ?', (category,))
            exists = any(f[0].replace(" ", "").lower() == norm_f for f in cursor.fetchall())

            if exists:
                skipped_count += 1
            else:
                cursor.execute('INSERT INTO formulas (category, formula_text) VALUES (?, ?)', (category, formula))
                added_count += 1
        except Exception:
            errors += 1 

    conn.commit()
    conn.close()

    result_msg = (
        f"📊 **Қосу нәтижесі:**\n\n"
        f"✅ Қосылды: `{added_count}`\n"
        f"⚠️ Базада бар: `{skipped_count}`\n"
        f"❌ Қате жолдар: `{errors}`"
    )
    await message.answer(result_msg)

@dp.message(Command("del"))
async def delete_formula(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    
    # Пәрменнен кейінгі мәтінді алу
    raw_text = message.text.replace("/del", "").strip()
    
    if not raw_text:
        await message.answer("❌ Үлгі: `/del мат 1 5` немесе:\nмат 1\nмат 2")
        return

    # Жолдарға бөлу
    lines = raw_text.split('\n')
    deleted_count = 0
    
    conn = sqlite3.connect('unt_bot.db')
    cursor = conn.cursor()

    # МАҢЫЗДЫ: Индекстер өзгеріп кетпеуі үшін үлкеннен кішіге қарай өшіреміз
    # Ол үшін алдымен тізімді жинап аламыз
    tasks = []
    for line in lines:
        try:
            parts = line.split()
            if len(parts) < 2: continue
            cat_key = parts[0].lower().replace(":", "")
            local_id = int(parts[1])
            tasks.append((cat_key, local_id))
        except: continue

    # Әр пән бойынша индекстерді кему ретімен сұрыптап өшіру
    for cat_key, local_id in sorted(tasks, key=lambda x: x[1], reverse=True):
        full_cat = CATEGORY_MAP.get(cat_key)
        if not full_cat: continue

        cursor.execute('SELECT id FROM formulas WHERE category = ? ORDER BY id', (full_cat,))
        rows = cursor.fetchall()
        
        if 0 < local_id <= len(rows):
            cursor.execute('DELETE FROM formulas WHERE id = ?', (rows[local_id-1][0],))
            deleted_count += 1

    conn.commit()
    conn.close()
    await message.answer(f"🗑 Өшірілді: `{deleted_count}` формула.")

@dp.message(Command("list"))
async def list_formulas(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect('unt_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT category, formula_text FROM formulas ORDER BY category, id')
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        await message.answer("📭 Дерекқор бос.")
        return
    grouped = {}
    for cat, text in rows:
        if cat not in grouped: grouped[cat] = []
        grouped[cat].append(text)
    await message.answer("📋 **Дерекқордағы формулалар:**")
    for cat, formulas in grouped.items():
        res = f"🔹 **{cat}** ({len(formulas)} дана):\n"
        for i, text in enumerate(formulas, 1):
            line = f"  {i}. `{text}`\n"
            if len(res) + len(line) > 4000:
                await message.answer(res)
                res = f"🔹 **{cat} (жалғасы):**\n"
            res += line
        await asyncio.sleep(0.1)
        await message.answer(res)

@dp.message(Command("send"))
async def broadcast_message(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    broadcast_text = message.text.replace("/send ", "").strip()
    if not broadcast_text or broadcast_text == "/send":
        await message.answer("❌ Хабарлама жазыңыз!")
        return

    conn = sqlite3.connect('unt_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()

    count, errors = 0, 0
    status_msg = await message.answer(f"⏳ Тарату басталды: 0/{len(users)}")

    for user in users:
        try:
            await bot.send_message(user[0], broadcast_text)
            count += 1
            if count % 20 == 0:
                await status_msg.edit_text(f"⏳ Тарату жүріп жатыр: {count}/{len(users)}")
            await asyncio.sleep(0.05)
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            await bot.send_message(user[0], broadcast_text)
            count += 1
        except Exception:
            errors += 1

    await status_msg.edit_text(f"✅ **Дайын!**\n📤 Жіберілді: `{count}`\n🚫 Қате: `{errors}`")

@dp.message(Command("reply"))
async def admin_reply(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = message.text.split(maxsplit=2)
        user_id = int(args[1])
        reply_text = args[2]
        await bot.send_message(user_id, f"🔔 **Автордан жауап:**\n\n{reply_text}")
        await message.answer(f"✅ Хабарлама {user_id} пайдаланушысына жіберілді.")
    except:
        await message.answer("❌ Үлгі: `/reply ID мәтін` ")

# ==========================================
# БОТТЫ ІСКЕ ҚОСУ
# ==========================================
async def main():
    init_db()
    await set_bot_commands(bot) # Меню орнату
    print("Бот іске қосылды!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот тоқтатылды.")