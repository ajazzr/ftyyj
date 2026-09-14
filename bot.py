import asyncio
import logging
import random
import time
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    LabeledPrice, PreCheckoutQuery, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Command

BOT_TOKEN = "8544816111:AAFnT_SjEWXUc9z1eFNtAVINVzTVyQdfCdc"
CHANNEL_ID = "@fasolevy_baron_channel"
CHANNEL_URL = "https://t.me/fasolevy_baron_channel"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def check_subscription(user_id: int, bot: Bot) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ("left", "kicked"):
            return False
        return True
    except Exception:
        return False

def sub_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Перейти в канал", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="🔄 Проверить подписку", callback_data="check_sub")],
    ])

async def need_sub(message: Message) -> bool:
    if not await check_subscription(message.from_user.id, bot):
        await message.answer(
            "❌ **Доступ ограничен!**\n• Чтобы управлять плантацией, вы должны быть подписаны на наш официальный канал.",
            reply_markup=sub_keyboard(),
            parse_mode="Markdown"
        )
        return True
    return False

conn = sqlite3.connect("bean_baron.db")
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS players (
  user_id INTEGER PRIMARY KEY,
  beans INTEGER DEFAULT 0,
  clicks INTEGER DEFAULT 0,
  fertilizer INTEGER DEFAULT 0,
  last_raid INTEGER DEFAULT 0,
  last_tap_time REAL DEFAULT 0,
  elf INTEGER DEFAULT 0,
  elf_last INTEGER DEFAULT 0,
  username TEXT DEFAULT '',
  last_daily_time INTEGER DEFAULT 0
)
""")
conn.commit()
for _sql in [
    "ALTER TABLE players ADD COLUMN elf INTEGER DEFAULT 0",
    "ALTER TABLE players ADD COLUMN elf_last INTEGER DEFAULT 0",
    "ALTER TABLE players ADD COLUMN username TEXT DEFAULT ''",
    "ALTER TABLE players ADD COLUMN last_tap_time INTEGER DEFAULT 0",
    "ALTER TABLE players ADD COLUMN last_daily_time INTEGER DEFAULT 0",
]:
    try:
        cur.execute(_sql)
        conn.commit()
    except Exception:
        pass

def get_player(user_id: int):
    row = cur.execute(
        "SELECT beans, clicks, fertilizer, last_raid, elf, elf_last, username, last_tap_time, last_daily_time FROM players WHERE user_id=?",
        (user_id,)
    ).fetchone()
    if not row:
        cur.execute("INSERT INTO players (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return (0, 0, 0, 0, 0, 0, '', 0, 0)
    return row

def save_name(user_id: int, name: str):
    cur.execute("UPDATE players SET username=? WHERE user_id=?", (name, user_id))
    conn.commit()

def get_title(beans: int) -> str:
    if beans <= 50:
        return "Нищий"
    if beans <= 300:
        return "Дачник"
    if beans <= 1000:
        return "Фермер"
    if beans <= 5000:
        return "Князь"
    return "Магнат"

FARM_NEWS = [
    "местная газета хвалит самый ровный ряд грядок",
    "сова прилетела и пересчитала запасы на складе",
    "эльф протер пыль на мешках и ушел на обход",
    "соседи спорят, чей боб круглее",
    "дождь прошел стороной, урожай в порядке",
]

def maybe_news() -> str:
    if random.random() < 0.2:
        return f"\n📰 Новости: {random.choice(FARM_NEWS)}"
    return ""

def collect_elf(user_id: int) -> int:
    beans, clicks, fert, last_raid, elf, elf_last, username, last_tap, last_daily = get_player(user_id)
    if not elf:
        return 0
    now = int(time.time())
    if not elf_last:
        cur.execute("UPDATE players SET elf_last=? WHERE user_id=?", (now, user_id))
        conn.commit()
        return 0
    mins = (now - elf_last) // 60
    if mins > 0:
        cur.execute("UPDATE players SET beans = beans + ?, elf_last = ? WHERE user_id=?", (mins, now, user_id))
        conn.commit()
        return mins
    return 0

kb_main = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌱 Тап"), KeyboardButton(text="🪲 Рейд"), KeyboardButton(text="💩 Навоз"), KeyboardButton(text="💼 Склад")],
        [KeyboardButton(text="🏆 Топ"), KeyboardButton(text="🧚 Эльф"), KeyboardButton(text="🔮 Колесо"), KeyboardButton(text="🎰 Кубки")],
        [KeyboardButton(text="🎁 Подарок"), KeyboardButton(text="💎 Магазин")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие"
)

def get_premium_keyboard():
    return kb_main

kb_thimbles = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="1"), KeyboardButton(text="2"), KeyboardButton(text="3")],
        [KeyboardButton(text="💼 Склад")],
    ],
    resize_keyboard=True
)

TAP = {"🌱 Тап", "🌱 Тапать Фасоль", "🌱 Собрать фасоль"}
RAID = {"🪲 Рейд", "🪲 Рейд!"}
FERT = {"💩 Навоз", "💩 Удобрить"}
STORE = {"💼 Склад", "💼 Склад и Стата", "👑 Баронство"}
TOP = {"🏆 Топ", "🏆 Зал Фасолевой Славы"}
ELF = {"🧚 Эльф", "🧚‍♂️ Нанять Фасолевого Эльфа"}
WHEEL = {"🔮 Колесо", "🔮 Фасолевое Колесо Удачи", "🔮 Колесо Судьбы"}
CUPS = {"🎰 Кубки", "🎰 Напёрстки", "🎲 Кубики"}
GIFT = {"🎁 Подарок", "🎁 Ежедневный Подарок"}
SHOP = {"💎 Магазин", "💎 Премиум Магазин", "💎 Премиум"}

@dp.message(CommandStart())
async def start(message: Message):
    get_player(message.from_user.id)
    save_name(message.from_user.id, message.from_user.first_name or "Барон")
    beans, *_ = get_player(message.from_user.id)
    await message.answer(
        f"🌱 **Имение открыто**\n• Владелец: {message.from_user.first_name}\n• Титул: {get_title(beans)}\n• Баланс: {beans} фасолей",
        reply_markup=get_premium_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery):
    if await check_subscription(call.from_user.id, bot):
        await call.message.answer(
            "🌱 **Подписка подтверждена**\n• Доступ открыт\n• Возвращайтесь к грядкам",
            reply_markup=get_premium_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await call.message.answer(
            "❌ **Доступ ограничен!**\n• Чтобы управлять плантацией, вы должны быть подписаны на наш официальный канал.",
            reply_markup=sub_keyboard(),
            parse_mode="Markdown"
        )
    await call.answer()

@dp.message(F.text.in_(TAP))
async def harvest(message: Message):
    if await need_sub(message):
        return
    beans, clicks, fert, last_raid, elf, elf_last, username, last_tap, last_daily = get_player(message.from_user.id)
    now = time.time()
    if last_tap and (now - float(last_tap)) < 3:
        remain = 3 - (now - float(last_tap))
        await message.answer(f"🌱 **Пауза**\n• Грядка отдыхает\n• Осталось: {remain:.1f} сек", parse_mode="Markdown")
        return
    base = 10 if random.random() < 0.05 else 1
    is_gold = base >= 10
    if fert > 0:
        base *= 3
        fert -= 1
    cur.execute("UPDATE players SET beans = beans + ?, clicks = clicks + 1, fertilizer = ?, last_tap_time = ? WHERE user_id = ?", (base, fert, now, message.from_user.id))
    conn.commit()
    beans += base
    head = "🌟 **Золотой урожай**" if is_gold else "🌱 **Сбор завершен**"
    await message.answer(f"{head}\n• Получено: +{base}\n• Баланс: {beans} фасолей\n• Удобрение: {fert}{maybe_news()}", parse_mode="Markdown")

@dp.message(F.text.in_(RAID))
async def raid(message: Message):
    if await need_sub(message):
        return
    beans, clicks, fert, last_raid, elf, elf_last, username, last_tap, last_daily = get_player(message.from_user.id)
    now = int(time.time())
    if now - (last_raid or 0) < 60:
        await message.answer(f"🪲 **Отряд занят**\n• Осталось: {60 - (now - last_raid)} сек\n• Баланс: {beans} фасолей", parse_mode="Markdown")
        return
    if beans < 10:
        await message.answer(f"🪲 **Нужны ресурсы**\n• Требуется: 10\n• Баланс: {beans} фасолей", parse_mode="Markdown")
        return
    win = random.random() < 0.5
    delta = max(10, int(beans * 0.5)) if win else -max(5, int(beans * 0.2))
    cur.execute("UPDATE players SET beans = beans + ?, last_raid = ? WHERE user_id=?", (delta, now, message.from_user.id))
    conn.commit()
    head = "⚔️ **Рейд: успех**" if win else "🪲 **Рейд: отбит**"
    await message.answer(f"{head}\n• Добыча: {delta:+d}\n• Баланс: {beans + delta} фасолей{maybe_news()}", parse_mode="Markdown")

@dp.message(F.text.in_(FERT))
async def fertilize(message: Message):
    if await need_sub(message):
        return
    beans, clicks, fert, last_raid, elf, elf_last, username, last_tap, last_daily = get_player(message.from_user.id)
    if fert > 0:
        await message.answer(f"🌸 **Поле активно**\n• Остаток: {fert} тапов\n• Баланс: {beans} фасолей", parse_mode="Markdown")
        return
    if beans < 50:
        await message.answer(f"💩 **Не хватает средств**\n• Нужно: 50\n• Баланс: {beans} фасолей", parse_mode="Markdown")
        return
    if random.random() < 0.3:
        cur.execute("UPDATE players SET beans = beans - 50, fertilizer = 10 WHERE user_id=?", (message.from_user.id,))
        conn.commit()
        await message.answer(f"🌸 **Поле усилено**\n• Списано: 50\n• Эффект: x3 на 10 тапов", parse_mode="Markdown")
    else:
        cur.execute("UPDATE players SET beans = beans - 50 WHERE user_id=?", (message.from_user.id,))
        conn.commit()
        await message.answer(f"💩 **Без эффекта**\n• Списано: 50\n• Баланс: {beans - 50} фасолей", parse_mode="Markdown")

@dp.message(F.text.in_(STORE))
async def warehouse(message: Message):
    if await need_sub(message):
        return
    save_name(message.from_user.id, message.from_user.first_name or "Барон")
    bonus = collect_elf(message.from_user.id)
    beans, clicks, fert, last_raid, elf, elf_last, username, last_tap, last_daily = get_player(message.from_user.id)
    title = get_title(beans)
    helper = "Активен" if elf else "Отсутствует"
    await message.answer(
        f"👑 **Профиль Барона**\n• Титул: {title}\n• 🥔 Фасоль на складе: {beans}\n• 🖱 Всего тапов: {clicks}\n• 🧪 Заряды навоза: {fert}\n• 🧚‍♂️ Помощник: {helper}{maybe_news()}",
        parse_mode="Markdown"
    )

@dp.message(Command("balance"))
async def balance_cmd(message: Message):
    await warehouse(message)

@dp.message(F.text.in_(TOP))
async def hall(message: Message):
    if await need_sub(message):
        return
    rows = cur.execute("SELECT username, user_id, beans FROM players ORDER BY beans DESC LIMIT 5").fetchall()
    if not rows:
        await message.answer("🏆 **Зал славы**\n• Список пуст", parse_mode="Markdown")
        return
    lines = ["🏆 **Зал славы**"]
    for i, (uname, uid, b) in enumerate(rows, 1):
        lines.append(f"• {i}. {uname or uid}: {b}")
    await message.answer("\n".join(lines[:6]), parse_mode="Markdown")

@dp.message(Command("top"))
async def top_cmd(message: Message):
    await hall(message)

@dp.message(F.text.in_(ELF))
async def hire_elf(message: Message):
    if await need_sub(message):
        return
    beans, clicks, fert, last_raid, elf, elf_last, username, last_tap, last_daily = get_player(message.from_user.id)
    if elf:
        await message.answer("🧚 **Эльф на службе**\n• Доход: 1 в минуту\n• Забор: на складе", parse_mode="Markdown")
        return
    if beans < 300:
        await message.answer(f"🧚 **Не хватает средств**\n• Нужно: 300\n• Баланс: {beans} фасолей", parse_mode="Markdown")
        return
    now = int(time.time())
    cur.execute("UPDATE players SET beans = beans - 300, elf = 1, elf_last = ? WHERE user_id=?", (now, message.from_user.id))
    conn.commit()
    await message.answer("🧚 **Эльф нанят**\n• Списано: 300\n• Доход: 1 в минуту", parse_mode="Markdown")

@dp.message(F.text.in_(WHEEL))
async def wheel(message: Message):
    if await need_sub(message):
        return
    beans, clicks, fert, last_raid, elf, elf_last, username, last_tap, last_daily = get_player(message.from_user.id)
    if beans < 20:
        await message.answer(f"🔮 **Не хватает средств**\n• Нужно: 20\n• Баланс: {beans} фасолей", parse_mode="Markdown")
        return
    cur.execute("UPDATE players SET beans = beans - 20 WHERE user_id=?", (message.from_user.id,))
    conn.commit()
    beans -= 20
    roll = random.random()
    if roll < 0.5:
        await message.answer(f"🔮 **Колесо: пусто**\n• Ставка: 20\n• Баланс: {beans} фасолей", parse_mode="Markdown")
    elif roll < 0.9:
        cur.execute("UPDATE players SET beans = beans + 40 WHERE user_id=?", (message.from_user.id,))
        conn.commit()
        await message.answer(f"🔮 **Колесо: x2**\n• Выигрыш: +40\n• Баланс: {beans + 40} фасолей", parse_mode="Markdown")
    else:
        cur.execute("UPDATE players SET beans = beans + 200 WHERE user_id=?", (message.from_user.id,))
        conn.commit()
        await message.answer(f"🔮 **Колесо: джекпот**\n• Выигрыш: +200\n• Баланс: {beans + 200} фасолей", parse_mode="Markdown")

@dp.message(F.text.in_(CUPS))
async def thimbles_menu(message: Message):
    if await need_sub(message):
        return
    await message.answer("🎲 **Наперстки**\n• Ставка: 10\n• Награда: 30", reply_markup=kb_thimbles, parse_mode="Markdown")

@dp.message(F.text.in_({"1", "2", "3", "🎰 1", "🎰 2", "🎰 3"}))
async def thimbles_play(message: Message):
    if await need_sub(message):
        return
    beans, clicks, fert, last_raid, elf, elf_last, username, last_tap, last_daily = get_player(message.from_user.id)
    if beans < 10:
        await message.answer(f"🎲 **Наперстки: нет средств**\n• Нужно: 10\n• Баланс: {beans} фасолей", reply_markup=get_premium_keyboard(), parse_mode="Markdown")
        return
    try:
        choice = int(message.text.split()[-1])
    except Exception:
        return
    win_cup = random.randint(1, 3)
    if choice == win_cup:
        cur.execute("UPDATE players SET beans = beans - 10 + 30 WHERE user_id=?", (message.from_user.id,))
        conn.commit()
        await message.answer(f"🎲 **Наперстки: победа**\n• Шарик под №{win_cup}\n• Награда: +30\n• Баланс: {beans + 20} фасолей", reply_markup=get_premium_keyboard(), parse_mode="Markdown")
    else:
        cur.execute("UPDATE players SET beans = beans - 10 WHERE user_id=?", (message.from_user.id,))
        conn.commit()
        await message.answer(f"🎲 **Наперстки: проигрыш**\n• Шарик был под №{win_cup} (Ваш выбор: №{choice})\n• Потеряно: 10 фасолей\n• Баланс: {beans - 10} фасолей", reply_markup=get_premium_keyboard(), parse_mode="Markdown")

@dp.message(F.text.in_(GIFT))
async def daily(message: Message):
    if await need_sub(message):
        return
    beans, clicks, fert, last_raid, elf, elf_last, username, last_tap, last_daily = get_player(message.from_user.id)
    now = int(time.time())
    cooldown = 24 * 60 * 60
    if last_daily and (now - int(last_daily)) < cooldown:
        left = cooldown - (now - int(last_daily))
        h = left // 3600
        m = (left % 3600) // 60
        await message.answer(f"🎁 **Подарок готовится**\n• Осталось: {h} ч {m} мин\n• Баланс: {beans} фасолей", parse_mode="Markdown")
        return
    if random.random() < 0.7:
        gift = random.randint(30, 80)
        cur.execute("UPDATE players SET beans = beans + ?, last_daily_time = ? WHERE user_id=?", (gift, now, message.from_user.id))
        conn.commit()
        await message.answer(f"🎁 **Подарок выдан**\n• Начислено: +{gift}\n• Баланс: {beans + gift} фасолей", parse_mode="Markdown")
    else:
        cur.execute("UPDATE players SET fertilizer = fertilizer + 5, last_daily_time = ? WHERE user_id=?", (now, message.from_user.id))
        conn.commit()
        await message.answer(f"🎁 **Подарок выдан**\n• Начислено: +5 удобрения\n• Остаток: {fert + 5} тапов", parse_mode="Markdown")

@dp.message(Command("daily"))
async def daily_cmd(message: Message):
    await daily(message)

@dp.message(F.text.in_(SHOP))
async def shop(message: Message):
    if await need_sub(message):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧪 Навоз +10 — 2 Stars", callback_data="buy_manure")],
        [InlineKeyboardButton(text="🧚 Контракт эльфа — 10 Stars", callback_data="buy_elf")],
    ])
    await message.answer("💎 **Премиум магазин**\n• Навоз +10: 2 Stars\n• Эльф: 10 Stars", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data == "buy_manure")
async def buy_manure(call: CallbackQuery):
    if not await check_subscription(call.from_user.id, bot):
        await call.message.answer("❌ **Доступ ограничен!**\n• Чтобы управлять плантацией, вы должны быть подписаны на наш официальный канал.", reply_markup=sub_keyboard(), parse_mode="Markdown")
        await call.answer()
        return
    await call.message.answer_invoice(title="Элитный навоз", description="+10 супер-тапов с урожаем x3", payload="elite_manure", currency="XTR", prices=[LabeledPrice(label="Навоз +10", amount=2)])
    await call.answer()

@dp.callback_query(F.data == "buy_elf")
async def buy_elf(call: CallbackQuery):
    if not await check_subscription(call.from_user.id, bot):
        await call.message.answer("❌ **Доступ ограничен!**\n• Чтобы управлять плантацией, вы должны быть подписаны на наш официальный канал.", reply_markup=sub_keyboard(), parse_mode="Markdown")
        await call.answer()
        return
    await call.message.answer_invoice(title="Контракт с эльфом", description="Пассивный доход: 1 фасоль в минуту", payload="elf_contract", currency="XTR", prices=[LabeledPrice(label="Эльф", amount=10)])
    await call.answer()

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def on_pay(message: Message):
    payload = message.successful_payment.invoice_payload
    if payload == "elite_manure":
        cur.execute("UPDATE players SET fertilizer = fertilizer + 10 WHERE user_id=?", (message.from_user.id,))
        conn.commit()
        await message.answer("💎 **Оплата прошла**\n• Начислено: +10 навоза\n• Эффект: x3", parse_mode="Markdown")
    elif payload == "elf_contract":
        now = int(time.time())
        cur.execute("UPDATE players SET elf = 1, elf_last = ? WHERE user_id=?", (now, message.from_user.id))
        conn.commit()
        await message.answer("💎 **Оплата прошла**\n• Эльф: активен\n• Доход: 1 в минуту", parse_mode="Markdown")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
