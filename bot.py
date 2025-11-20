# bot.py
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
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, ADMIN_CHAT_ID
from db import init_db, create_application, get_user_applications


# === КОНСТАНТЫ ===

WEBAPP_URL = "https://aramyanvs.github.io/exam-bot-webapp/?v=3"


# === КЛАВИАТУРЫ ===

def main_menu() -> InlineKeyboardMarkup:
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


# === DISPATCHER ===

dp = Dispatcher()


# === ОБРАБОТЧИКИ ===

@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = (
        "Здравствуйте! 👋\n\n"
        "Это бот приёмной комиссии Московского экономического института\n"
        "для записи на вступительные испытания.\n\n"
        "Нажмите «📋 Заполнить анкету», заполните форму и отправьте заявку.\n"
        "После обработки вы получите доступ в личный кабинет для сдачи испытаний."
    )
    await message.answer(text, reply_markup=main_menu())


@dp.callback_query(F.data == "myapps")
async def cb_myapps(call: CallbackQuery) -> None:
    await call.answer()

    apps = get_user_applications(call.from_user.id)

    if not apps:
        await call.message.answer(
            "У вас пока нет поданных заявок.", reply_markup=main_menu()
        )
        return

    lines = []
    for app in apps:
        lines.append(
            f"• №{app['id']}: {app['direction']} — {app['program_level']} — {app['status']}"
        )

    text = "Ваши заявки:\n\n" + "\n".join(lines)
    await call.message.answer(text, reply_markup=main_menu())


@dp.message()
async def universal_handler(message: Message) -> None:
    """
    1) Если пришли данные из WebApp (web_app_data) — обрабатываем заявку
    2) Иначе — обычный текст, просто логируем
    """

    # === 1. ДАННЫЕ ИЗ WEBAPP ===
    if message.web_app_data is not None:
        raw = message.web_app_data.data
        logging.info("[WEBAPP] Получены сырые данные: %s", raw)

        try:
            data = json.loads(raw)
        except Exception as e:
            logging.exception("Не удалось распарсить JSON из WebApp: %s", e)
            await message.answer(
                "Не удалось прочитать данные заявки. Попробуйте ещё раз чуть позже."
            )
            return

        fio = (data.get("fio") or "").strip()
        birth = (data.get("birth") or "").strip()
        email = (data.get("email") or "").strip()
        doc_type = (data.get("doc_type") or "").strip()
        level = (data.get("level") or "").strip()
        direction = (data.get("direction") or "").strip()

        user_id = message.from_user.id
        username = message.from_user.username or ""

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
                "Произошла ошибка при сохранении заявки. "
                "Напишите, пожалуйста, в приёмную комиссию."
            )
            return

        logging.info("[WEBAPP] Создана заявка #%s для user_id=%s", app_id, user_id)

        # ответ пользователю
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

        # уведомление админу
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
            logging.exception("Не удалось отправить уведомление админу: %s", e)

        return  # ВАЖНО: выходим, чтобы не обрабатывать дальше как обычный текст

    # === 2. Обычный текст ===
    logging.info(
        "[TEXT] Сообщение от %s (@%s): %s",
        message.from_user.id,
        message.from_user.username,
        (message.text or "").replace("\n", "\\n") if message.text else "",
    )
    # Можно ответить что-то нейтральное:
    # await message.answer("Используйте, пожалуйста, кнопки меню.", reply_markup=main_menu())


# === ЗАПУСК БОТА ===

async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    logging.info("[INFO] Инициализация БД…")
    init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    logging.info("[INFO] Бот запущен, стартуем polling…")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
