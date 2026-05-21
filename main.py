import os
import time
import json
import requests
import base64
import logging
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
    """Load birthdays from GitHub."""
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
    """Save birthdays to GitHub."""
    try:
        content = json.dumps(birthdays, ensure_ascii=False, indent=2)
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        # Get current SHA
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

def send_message(text, chat_id=None):
    """Send message to Telegram."""
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
    """Check and send birthday notifications."""
    birthdays = load_birthdays()
    today = datetime.now()
    found = False
    for days_before in [4, 3]:
        target = today + timedelta(days=days_before)
        target_str = target.strftime("%d.%m")
        for person in birthdays:
            if person["date"] == target_str:
                found = True
                if days_before == 4:
                    header = "⚠️ <b>Напоминание — 4 дня до дня рождения!</b>"
                else:
                    header = "🎂 <b>Напоминание — 3 дня до дня рождения!</b>"
                msg = (
                    f"{header}\n\n"
                    f"👤 <b>{person['name']}</b>\n"
                    f"🗓 Дата: {person['date']}\n\n"
                    f"📌 <b>Порядок действий:</b>\n"
                    f"1️⃣ Сначала <b>удалите {person['name']}</b> из этой группы\n"
                    f"2️⃣ Затем обсудите подарок 🎁\n\n"
                    f"Не забудьте поздравить именинника! 🥳"
                )
                send_message(msg)
    if not found:
        logger.info("No birthdays in next 3-4 days")

# === TELEGRAM COMMAND HANDLERS ===

async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add new person. Usage: /add Иванов Иван 15.03"""
    if str(update.effective_chat.id) != str(CHAT_ID):
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Неверный формат.\n\n"
            "Используйте:\n"
            "<code>/add Иванов Иван Иванович 15.03</code>\n\n"
            "Дата в формате ДД.ММ",
            parse_mode="HTML"
        )
        return

    # Last arg is date, rest is name
    date_str = args[-1]
    name = " ".join(args[:-1])

    # Validate date format
    try:
        datetime.strptime(date_str, "%d.%m")
    except ValueError:
        await update.message.reply_text(
            f"❌ Неверный формат даты: <b>{date_str}</b>\n"
            f"Нужно: ДД.ММ (например: <b>15.03</b>)",
            parse_mode="HTML"
        )
        return

    birthdays = load_birthdays()

    # Check duplicate
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
            f"✅ Добавлен!\n\n"
            f"👤 <b>{name}</b>\n"
            f"🗓 Дата рождения: <b>{date_str}</b>\n\n"
            f"📋 Всего в списке: {len(birthdays)} человек",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("❌ Ошибка при сохранении. Попробуйте снова.")

async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove person. Usage: /remove Иванов Иван"""
    if str(update.effective_chat.id) != str(CHAT_ID):
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Укажите имя.\n\nПример: <code>/remove Иванов Иван</code>",
            parse_mode="HTML"
        )
        return

    name = " ".join(context.args)
    birthdays = load_birthdays()
    original_len = len(birthdays)

    # Search case-insensitive
    found_name = None
    new_list = []
    for p in birthdays:
        if p["name"].lower() == name.lower():
            found_name = p["name"]
        else:
            new_list.append(p)

    if found_name is None:
        await update.message.reply_text(
            f"❌ <b>{name}</b> не найден в списке.\n\n"
            f"Используйте /list чтобы посмотреть всех.",
            parse_mode="HTML"
        )
        return

    if save_birthdays(new_list):
        await update.message.reply_text(
            f"✅ Удалён!\n\n"
            f"👤 <b>{found_name}</b>\n\n"
            f"📋 Осталось в списке: {len(new_list)} человек",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("❌ Ошибка при сохранении.")

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all birthdays."""
    if str(update.effective_chat.id) != str(CHAT_ID):
        return

    birthdays = load_birthdays()
    if not birthdays:
        await update.message.reply_text("📋 Список пуст.")
        return

    text = f"📋 <b>Список дней рождения ({len(birthdays)} чел.):</b>\n\n"
    for i, p in enumerate(birthdays, 1):
        text += f"{i}. {p['date']} — {p['name']}\n"

    text += "\n<i>Команды:\n/add Имя Фамилия 15.03\n/remove Имя Фамилия</i>"
    await update.message.reply_text(text, parse_mode="HTML")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help."""
    await update.message.reply_text(
        "🎂 <b>Birthday Bot — команды:</b>\n\n"
        "/add Иван Иванов 15.03 — добавить человека\n"
        "/remove Иван Иванов — удалить человека\n"
        "/list — показать весь список\n"
        "/help — эта справка",
        parse_mode="HTML"
    )

# === SCHEDULER ===

def run_scheduler():
    """Run daily check at 09:00."""
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

# === MAIN ===

import threading

print("🎂 Birthday Bot v2 started!")
print(f"BOT_TOKEN: {'set' if BOT_TOKEN else 'NOT SET'}")
print(f"CHAT_ID: {CHAT_ID}")
print(f"GITHUB_TOKEN: {'set' if GITHUB_TOKEN else 'NOT SET'}")
print(f"GITHUB_REPO: {GITHUB_REPO}")

# Load and show initial list
birthdays = load_birthdays()
print(f"Loaded {len(birthdays)} birthdays from GitHub")

# Start scheduler in background thread
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

# Start bot
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("add", cmd_add))
app.add_handler(CommandHandler("remove", cmd_remove))
app.add_handler(CommandHandler("list", cmd_list))
app.add_handler(CommandHandler("help", cmd_help))

print("Bot is running with commands: /add /remove /list /help")
app.run_polling(drop_pending_updates=True)
