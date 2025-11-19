import asyncio
import json
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)

from config import BOT_TOKEN, ADMIN_CHAT_ID
from db import init_db, create_application, get_user_applications


# === НАСТРОЙКИ ===

WEBAPP_URL = "https://aramyanvs.github.io/exam-bot-webapp/"  # твой GitHub Pages


# === КЛАВИАТУРЫ ===

def main_menu() -> InlineKeyboardMarkup:
    """
    Главное меню бота:
    - кнопка для открытия мини-приложения
    - кнопка "Мои заявки"
    """
    kb = [
        [
            InlineKeyboardButton(
                text="📋 Заполнить анкету",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        ],
        [
            InlineKeyboardButton(
                text="📄 Мои заявки",
                callback_data="myapps",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# === ОБРАБОТЧИКИ ===

dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = (
        "Здравствуйте! 👋\n\n"
        "Это бот приёмной комиссии МЭИ для записи на вступительные испытания.\n\n"
        "Нажмите «📋 Заполнить анкету», заполните форму и отправьте заявку.\n"
        "После обработки вы получите доступ в личный кабинет для сдачи вступительных испытаний."
    )
    await message.answer(text, reply_markup=main_menu())


@dp.callback_query(F.data == "myapps")
async def cb_myapps(call: CallbackQuery) -> None:
    """
    Показать пользователю список его заявок.
    ВАЖНО: отправляем НОВОЕ сообщение, а не edit_text, чтобы не ловить
    ошибку 'message is not modified'.
    """
    await call.answer()  # убираем "часики"

    apps = get_user_applications(call.from_user.id)

    if not apps:
        await call.message.answer(
            "У вас пока нет поданных заявок.", reply_markup=main_menu()
        )
        return

    lines = []
    for app in apps:
        # ожидаем, что db.get_user_applications возвращает словари с такими ключами:
        # id, direction, program_level, status
        lines.append(
            f"• №{app['id']}: {app['direction']} — {app['program_level']} — {app['status']}"
        )

    text = "Ваши заявки:\n\n" + "\n".join(lines)
    await call.message.answer(text, reply_markup=main_menu())


@dp.message(F.web_app_data)
async def handle_webapp_data(message: Message) -> None:
    """
    Обработка данных из мини-приложения (Telegram WebApp).
    В app.js должно быть примерно:
        Telegram.WebApp.sendData(JSON.stringify({ ... }))
    """
    raw = message.web_app_data.data

    logging.info("[WEBAPP] Получены сырые данные: %s", raw)

    try:
        data = json.loads(raw)
    except Exception as e:
        logging.exception("Не удалось распарсить JSON из WebApp: %s", e)
        await message.answer(
            "Не удалось прочитать данные заявки. Попробуйте ещё раз немного позже."
        )
        return

    # Достаём поля из JSON (имена должны совпадать с app.js)
    fio = (data.get("fio") or "").strip()
    birth = (data.get("birth") or "").strip()
    email = (data.get("email") or "").strip()
    doc_type = (data.get("doc_type") or "").strip()
    level = (data.get("level") or "").strip()          # Бакалавриат / Магистратура / Аспирантура
    direction = (data.get("direction") or "").strip()  # Направление подготовки

    user_id = message.from_user.id
    username = message.from_user.username or ""

    # Сохраняем в базу
    try:
        app_id = create_application(
            user_id=user_id,
            username=username,
            fio=fio,
            birth=birth,
            email=email,
            doc_type=doc_type,
            program_level=level,
            direction=direction,
        )
    except Exception as e:
        logging.exception("Ошибка при сохранении заявки в БД: %s", e)
        await message.answer(
            "Произошла ошибка при сохранении заявки. Напишите, пожалуйста, в приёмную комиссию."
        )
        return

    logging.info("[WEBAPP] Создана заявка #%s для user_id=%s", app_id, user_id)

    # Сообщение пользователю
    text_user = (
        f"✅ Ваша заявка №{app_id} на вступительные испытания принята.\n\n"
        f"Данные из анкеты:\n"
        f"• ФИО: {fio}\n"
        f"• Дата рождения: {birth}\n"
        f"• Email: {email}\n"
        f"• Документ об образовании: {doc_type}\n"
        f"• Уровень: {level}\n"
        f"• Направление: {direction}\n\n"
        "После обработки заявки вам будет направлен доступ в личный кабинет "
        "для сдачи вступительных испытаний."
    )
    await message.answer(text_user, reply_markup=main_menu())

    # Уведомление админу
    admin_text = (
        "📥 Новая заявка на вступительные испытания\n\n"
        f"№ {app_id}\n\n"
        f"👤 Абитуриент: {fio}\n"
        f"Telegram: @{username or '—'} (id: {user_id})\n\n"
        f"📄 Документ: {doc_type}\n"
        f"🎓 Уровень: {level}\n"
        f"📚 Направление: {direction}\n"
        f"📧 Email: {email}\n"
        f"📅 Дата рождения: {birth}\n"
    )

    try:
        await message.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_text,
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        # не падаем, если админу не удалось отправить (например, не написал боту)
        logging.exception("Не удалось отправить уведомление админу: %s", e)


# === ЗАПУСК ===

async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    logging.info("[INFO] Инициализация БД…")
    init_db()

    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)

    logging.info("[INFO] Бот запущен, стартуем polling…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
