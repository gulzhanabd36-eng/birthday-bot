import os
import time
import json
import random
import requests
import base64
import logging
import threading
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "gulzhanabd36-eng/birthday-bot")

GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def load_birthdays():
    try:
        r = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/birthdays.json",
            headers=GITHUB_HEADERS, timeout=15
        )
        if r.status_code == 200:
            content = base64.b64decode(r.json()["content"]).decode("utf-8")
            return json.loads(content)
    except Exception as e:
        logger.error(f"Load error: {e}")
    return []

def save_birthdays(birthdays):
    try:
        content = json.dumps(birthdays, ensure_ascii=False, indent=2)
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        r = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/birthdays.json",
            headers=GITHUB_HEADERS, timeout=10
        )
        payload = {"message": "Update birthdays", "content": encoded}
        if r.status_code == 200:
            payload["sha"] = r.json().get("sha", "")
        requests.put(
            f"https://api.github.com/repos/{GITHUB_REPO}/contents/birthdays.json",
            headers=GITHUB_HEADERS, json=payload, timeout=15
        )
        return True
    except Exception as e:
        logger.error(f"Save error: {e}")
        return False

def get_random_collector(exclude_name: str = "") -> str:
    birthdays = load_birthdays()
    candidates = [p["name"] for p in birthdays if p["name"] != exclude_name]
    if not candidates:
        return "кто-нибудь из команды"
    return random.choice(candidates)

def send_message(text, chat_id=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            json={"chat_id": chat_id or CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=30
        )
        return r.json()
    except Exception as e:
        logger.error(f"Send error: {e}")
        return {}

def check_birthdays():
    birthdays = load_birthdays()
    today = datetime.now()
    for days_before in [4, 3]:
        target = today + timedelta(days=days_before)
        target_str = target.strftime("%d.%m")
        for person in birthdays:
            if person["date"] == target_str:
                collector = get_random_collector(exclude_name=person["name"])
                if days_before == 4:
                    header = "⚠️ <b>Напоминание — 4 дня до дня рождения!</b>"
                else:
                    header = "🎂 <b>Напоминание — 3 дня до дня рождения!</b>"
                msg = (
                    f"{header}\n\n"
                    f"👤 <b>{person['name']}</b>\n"
                    f"🗓 Дата: {person['date']}\n\n"
                    f"📌 <b>Порядок действий:</b>\n"
                    f"1️⃣ Сначала <b>удалите {person['name']}</b> из группы\n"
                    f"2️⃣ Затем обсудите подарок 🎁\n\n"
                    f"💰 <b>Сбор денег:</b> {collector}\n\n"
                    f"Не забудьте поздравить именинника! 🥳"
                )
                send_message(msg)
                logger.info(f"Sent notification for {person['name']}, collector: {collector}")

# === КОМАНДЫ ===

async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != str(CHAT_ID):
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Неверный формат.\n\nИспользуйте:\n"
            "<code>/add Иванов Иван 15.03</code>\n\nДата: ДД.ММ",
            parse_mode="HTML"
        )
        return
    date_str = args[-1]
    name = " ".join(args[:-1])
    try:
        datetime.strptime(date_str, "%d.%m")
    except ValueError:
        await update.message.reply_text(
            f"❌ Неверный формат даты: <b>{date_str}</b>\nНужно: ДД.ММ (например: <b>15.03</b>)",
            parse_mode="HTML"
        )
        return
    birthdays = load_birthdays()
    for p in birthdays:
        if p["name"].lower() == name.lower():
            await update.message.reply_text(
                f"⚠️ <b>{name}</b> уже есть в списке (дата: {p['date']})",
                parse_mode="HTML"
            )
            return
    birthdays.append({"date": date_str, "name": name})
    birthdays.sort(key=lambda x: (x["date"][3:5], x["date"][0:2]))
    if save_birthdays(birthdays):
        await update.message.reply_text(
            f"✅ Добавлен!\n\n👤 <b>{name}</b>\n🗓 Дата: <b>{date_str}</b>\n\n📋 Всего: {len(birthdays)} чел.",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("❌ Ошибка при сохранении.")

async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != str(CHAT_ID):
        return
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите имя.\nПример: <code>/remove Иванов Иван</code>",
            parse_mode="HTML"
        )
        return
    name = " ".join(context.args)
    birthdays = load_birthdays()
    found_name = None
    new_list = []
    for p in birthdays:
        if p["name"].lower() == name.lower():
            found_name = p["name"]
        else:
            new_list.append(p)
    if found_name is None:
        await update.message.reply_text(
            f"❌ <b>{name}</b> не найден.\nИспользуйте /list чтобы посмотреть всех.",
            parse_mode="HTML"
        )
        return
    if save_birthdays(new_list):
        await update.message.reply_text(
            f"✅ Удалён!\n\n👤 <b>{found_name}</b>\n\n📋 Осталось: {len(new_list)} чел.",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("❌ Ошибка при сохранении.")

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != str(CHAT_ID):
        return
    birthdays = load_birthdays()
    if not birthdays:
        await update.message.reply_text("📋 Список пуст.")
        return
    text = f"📋 <b>Список дней рождения ({len(birthdays)} чел.):</b>\n\n"
    for i, p in enumerate(birthdays, 1):
        text += f"{i}. {p['date']} — {p['name']}\n"
    text += "\n<i>/add Имя 15.03 | /remove Имя | /collector</i>"
    await update.message.reply_text(text, parse_mode="HTML")

async def cmd_collector(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != str(CHAT_ID):
        return
    # Check if birthday person name is passed as argument
    exclude = " ".join(context.args) if context.args else ""
    collector = get_random_collector(exclude_name=exclude)
    if exclude:
        msg = (
            f"🎲 <b>Рандомный сборщик денег</b>\n\n"
            f"🎂 Именинник: <b>{exclude}</b>\n"
            f"💰 Собирает деньги: <b>{collector}</b>\n\n"
            f"Удачи! 🍀"
        )
    else:
        msg = (
            f"🎲 <b>Рандомный сборщик денег</b>\n\n"
            f"💰 Собирает деньги: <b>{collector}</b>\n\n"
            f"Удачи! 🍀"
        )
    await update.message.reply_text(msg, parse_mode="HTML")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎂 <b>Birthday Bot — команды:</b>\n\n"
        "/add Иван Иванов 15.03 — добавить\n"
        "/remove Иван Иванов — удалить\n"
        "/list — весь список\n"
        "/collector — выбрать рандомного сборщика\n"
        "/collector Иван Иванов — выбрать сборщика (исключая именинника)\n"
        "/help — эта справка",
        parse_mode="HTML"
    )

def run_scheduler():
    CHECK_HOUR = 9
    while True:
        now = datetime.now()
        if now.hour == CHECK_HOUR and now.minute == 0:
            logger.info(f"Running birthday check at {now}")
            check_birthdays()
            time.sleep(61)
        else:
            next_check = now.replace(hour=CHECK_HOUR, minute=0, second=0, microsecond=0)
            if now >= next_check:
                next_check += timedelta(days=1)
            sleep_secs = (next_check - now).total_seconds()
            logger.info(f"Next check at {next_check.strftime('%H:%M')} (sleep {sleep_secs:.0f}s)")
            time.sleep(min(sleep_secs, 3600))

print("🎂 Birthday Bot v3 started!")
print(f"BOT_TOKEN: {'set' if BOT_TOKEN else 'NOT SET'}")
print(f"CHAT_ID: {CHAT_ID}")
print(f"GITHUB_TOKEN: {'set' if GITHUB_TOKEN else 'NOT SET'}")
print(f"GITHUB_REPO: {GITHUB_REPO}")

birthdays = load_birthdays()
print(f"Loaded {len(birthdays)} birthdays from GitHub")

scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("add", cmd_add))
app.add_handler(CommandHandler("remove", cmd_remove))
app.add_handler(CommandHandler("list", cmd_list))
app.add_handler(CommandHandler("collector", cmd_collector))
app.add_handler(CommandHandler("help", cmd_help))

print("Bot running: /add /remove /list /collector /help")
app.run_polling(drop_pending_updates=True)
