import os
import re
import smtplib
import dns.resolver
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Настройки для SMTP сервера
SMTP_CONFIG = {
    "server": os.getenv("SMTP_SERVER", "smtp.yandex.ru"),
    "port": int(os.getenv("SMTP_PORT", 465)),
    "username": os.getenv("SMTP_USER", "example@yandex.ru"),
    "password": os.getenv("SMTP_PASSWORD", "password"),
}

# Токен для Telegram бота
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN", "bot_token")

# Статусы пользователей
user_states = {}


# Валидация email (формат и MX-домены)
def validate_email(email: str) -> bool:
    email_pattern = r"^[\w.-]+@[a-zA-Z\d.-]+\.[a-zA-Z]{2,}$"
    if not re.fullmatch(email_pattern, email):
        return False

    try:
        domain = email.split("@")[1]
        dns.resolver.resolve(domain, "MX")
        return True
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return False


# Обработчик команды /start
async def start_command(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user_states[user_id] = {"email": None, "message": None}
    await update.message.reply_text("Укажите email для отправки сообщения.")


# Обработчик входящих сообщений
async def process_message(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user_input = update.message.text

    if user_id not in user_states:
        await update.message.reply_text("/start.")
        return

    user_info = user_states[user_id]

    if user_info["email"] is None:
        if validate_email(user_input):
            user_info["email"] = user_input
            await update.message.reply_text("Email принят! Напишите текст сообщения.")
        else:
            await update.message.reply_text("Неправильный email.")
    elif user_info["message"] is None:
        user_info["message"] = user_input
        recipient_email = user_info["email"]

        try:
            send_email_via_smtp(recipient_email, user_input)
            await update.message.reply_text(f"Cообщение отправлено на {recipient_email}!")
        except Exception as e:
            await update.message.reply_text(f"Не удалось отправить сообщение: {e}")

        # Сброс состояния пользователя
        del user_states[user_id]


# Функция для отправки email через SMTP
def send_email_via_smtp(to_email: str, message_body: str) -> None:
    email_message = MIMEMultipart()
    email_message["From"] = SMTP_CONFIG["username"]
    email_message["To"] = to_email
    email_message["Subject"] = "Уведомление от Telegram-бота"
    email_message.attach(MIMEText(message_body, "plain"))

    with smtplib.SMTP_SSL(SMTP_CONFIG["server"], SMTP_CONFIG["port"]) as smtp_server:
        smtp_server.login(SMTP_CONFIG["username"], SMTP_CONFIG["password"])
        smtp_server.send_message(email_message)


# Основной запуск бота
def main():


    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))

    # Запуск бота
    application.run_polling()


if __name__ == "__main__":
    main()
