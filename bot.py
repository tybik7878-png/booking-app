import base64
import json
import os
import requests
from telebot import TeleBot, types

# === КОНФИГУРАЦИЯ ===
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = -1003994862974  # ID чата/канала для админ-уведомлений

# Данные GitHub для базы данных
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NAME = "tybik7878-png/booking-app"
FILE_PATH = "bookings.json"

WEB_APP_URL = "https://tybik7878-png.github.io/booking-app/"

# Картинка приветствия
WELCOME_IMAGE_URL = "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=800"

bot = TeleBot(TOKEN)


# === РАБОТА С GITHUB API ===
def save_booking_to_github(date_str, time_str):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"

    # Использование Bearer и User-Agent для стабильной работы API GitHub
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "BookingBotApp",
    }

    try:
        # 1. Читаем текущий bookings.json с GitHub
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            file_data = res.json()
            sha = file_data["sha"]
            content = base64.b64decode(file_data["content"]).decode("utf-8")
            bookings = json.loads(content)
        else:
            sha = None
            bookings = {}

        # 2. Добавляем новое забронированное время
        if date_str not in bookings:
            bookings[date_str] = []
        if time_str not in bookings[date_str]:
            bookings[date_str].append(time_str)

        # 3. Обновляем файл на GitHub
        new_content = base64.b64encode(
            json.dumps(bookings, indent=2, ensure_ascii=False).encode("utf-8")
        ).decode("utf-8")

        payload = {
            "message": f"Бронь: {date_str} {time_str}",
            "content": new_content,
        }
        if sha:
            payload["sha"] = sha

        put_res = requests.put(url, headers=headers, json=payload)
        if put_res.status_code in [200, 201]:
            print(f"✅ Успешно сохранено на GitHub: {date_str} {time_str}")
            return True
        else:
            print("❌ Ошибка записи на GitHub:", put_res.json())
            return False

    except Exception as e:
        print("❌ Ошибка при работе с GitHub API:", e)
        return False


# === КОМАНДЫ БОТА ===
@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    web_app_btn = types.KeyboardButton(
        text="📅 Записаться на услугу",
        web_app=types.WebAppInfo(url=WEB_APP_URL),
    )
    location_btn = types.KeyboardButton(text="📍 Где мы находимся?")
    contacts_btn = types.KeyboardButton(text="📞 Контакты")

    markup.add(web_app_btn)
    markup.add(location_btn, contacts_btn)

    welcome_text = (
        f"👋 **Привет, {message.from_user.first_name}!**\n\n"
        f"Добро пожаловать в **Barber & Studio**! ✂️\n\n"
        f"⚠️ **ВНИМАНИЕ:** Данный бот создан в **демонстрационных/тестовых целях**. "
        f"Салона не существует, реальные услуги не оказываются!\n\n"
        f"Для тестирования онлайн-записи нажмите на кнопку ниже:"
    )

    try:
        bot.send_photo(
            message.chat.id,
            photo=WELCOME_IMAGE_URL,
            caption=welcome_text,
            reply_markup=markup,
            parse_mode="Markdown",
        )
    except Exception:
        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=markup,
            parse_mode="Markdown",
        )


@bot.message_handler(func=lambda message: message.text == "📍 Где мы находимся?")
def send_location(message):
    bot.send_message(
        message.chat.id,
        "📍 **Тестовый адрес:**\nг. Актобе, проспект Абилкайыр Хана, 42\n🕒 **Режим работы:** ежедневно с 08:00 до 22:00",
        parse_mode="Markdown",
    )
    bot.send_location(message.chat.id, latitude=50.2882, longitude=57.1704)


@bot.message_handler(func=lambda message: message.text == "📞 Контакты")
def send_contacts(message):
    bot.send_message(
        message.chat.id,
        "📞 **Контакты (Тестовые):**\n• Телефон: +7 (777) 000-00-00\n• Instagram: @barber_studio_aktobe\n\n*(Бот работает в тестовом режиме)*",
        parse_mode="Markdown",
    )


# === ОБРАБОТКА ДАННЫХ ИЗ WEB APP ===
@bot.message_handler(content_types=["web_app_data"])
def handle_web_app_data(message):
    try:
        data = json.loads(message.web_app_data.data)
        service = data.get("service", "Стрижка")
        date_str = data.get("date")
        time_str = data.get("time")
        user = message.from_user

        # 1. Сохраняем бронь в GitHub
        saved = save_booking_to_github(date_str, time_str)

        # 2. Сообщение для клиента
        client_text = (
            f"🎉 **Тестовая запись оформлена!**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✂️ **Услуга:** {service}\n"
            f"📅 **Дата:** `{date_str}`\n"
            f"⏰ **Время:** `{time_str}`\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"📍 *Адрес:* г. Актобе, пр. Абилкайыр Хана, 42\n"
            f"*(Напоминаем: это демонстрационная запись)*"
        )
        bot.send_message(message.chat.id, client_text, parse_mode="Markdown")

        # 3. Отправка уведомления админу / в канал
        username_str = f"@{user.username}" if user.username else "без юзернейма"
        status_icon = "✅" if saved else "⚠️ (Ошибка записи в базу)"

        admin_text = (
            f"🚨 **НОВАЯ ЗАПИСЬ В БОТЕ!** {status_icon}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Клиент:** {user.first_name} ({username_str})\n"
            f"🆔 **ID:** `{user.id}`\n"
            f"✂️ **Услуга:** {service}\n"
            f"📅 **Дата:** `{date_str}`\n"
            f"⏰ **Время:** `{time_str}`\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")

    except Exception as e:
        print("Ошибка обработки записи:", e)
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка при обработке записи. Попробуйте еще раз.",
        )


if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling(skip_pending=True, timeout=60)
