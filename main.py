import os
import time
import requests
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

BIRTHDAYS = [
    ("23.01", "Артур Ким"),
    ("10.02", "Евгений Усатов"),
    ("10.02", "Зайцев Максим Андреевич"),
    ("12.02", "Пашкевич Данил Андреевич"),
    ("01.03", "Тимур Рыспеков Олегович"),
    ("19.03", "Бакиев Анвар"),
    ("07.04", "Шиндаков Максим Сергеевич / Шиндаков Максут Сержулы"),
    ("24.04", "Сапаков Алихан Аскарович"),
    ("04.05", "Тума Толеген"),
    ("15.05", "Абдыманапова Гульжан"),
    ("26.06", "Майжаканова Перизат"),
    ("25.07", "Полонский Владислав Сергеевич"),
    ("12.08", "Зобков Микаэль Феликсович"),
    ("23.08", "Кузнецов Артем Юрьевич"),
    ("30.09", "Элла Байысбаева"),
    ("16.11", "Айгерим Ногайбаева"),
    ("03.12", "Бакиев Азиз Адылжарович"),
    ("05.12", "Лобанов Георгий Андреевич"),
]

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=30
        )
        print(f"Send result: {r.status_code} {r.text[:100]}")
        return r.json()
    except Exception as e:
        print(f"Send error: {e}")
        return {}

def check_birthdays():
    today = datetime.now()
    found = False
    for days_before in [4, 3]:
        target = today + timedelta(days=days_before)
        target_str = target.strftime("%d.%m")
        for bday_date, name in BIRTHDAYS:
            if bday_date == target_str:
                found = True
                if days_before == 4:
                    header = "⚠️ <b>Напоминание — 4 дня до дня рождения!</b>"
                else:
                    header = "🎂 <b>Напоминание — 3 дня до дня рождения!</b>"
                msg = (
                    f"{header}\n\n"
                    f"👤 <b>{name}</b>\n"
                    f"🗓 Дата: {bday_date}\n\n"
                    f"📌 <b>Порядок действий:</b>\n"
                    f"1️⃣ Сначала <b>удалите {name}</b> из этой группы\n"
                    f"2️⃣ Затем обсудите подарок 🎁\n\n"
                    f"Не забудьте поздравить именинника! 🥳"
                )
                send_message(msg)
    if not found:
        print(f"No birthdays in next 3-4 days")

print("🎂 Birthday bot started!")
print(f"BOT_TOKEN: {'set' if BOT_TOKEN else 'NOT SET'}")
print(f"CHAT_ID: {'set' if CHAT_ID else 'NOT SET'}")

CHECK_HOUR = 9

while True:
    now = datetime.now()
    if now.hour == CHECK_HOUR and now.minute == 0:
        print(f"[{now}] Running birthday check...")
        check_birthdays()
        time.sleep(61)
    else:
        next_check = now.replace(hour=CHECK_HOUR, minute=0, second=0, microsecond=0)
        if now >= next_check:
            next_check += timedelta(days=1)
        sleep_secs = (next_check - now).total_seconds()
        print(f"[{now}] Sleeping {sleep_secs:.0f}s until next check at {next_check.strftime('%H:%M')}")
        time.sleep(min(sleep_secs, 3600))
