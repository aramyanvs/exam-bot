import asyncio
import json

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    CallbackQuery,
)
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_CHAT_ID
from db import (
    init_db,
    create_application,
    get_user_applications,
    get_application,
    set_status,
)


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Заполнить анкету",
                    web_app=WebAppInfo(
                        url="https://aramyanvs.github.io/exam-bot-webapp/"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📄 Мои заявки",
                    callback_data="myapps",
                )
            ],
        ]
    )


def admin_decision_kb(app_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить", callback_data=f"approve:{app_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить", callback_data=f"reject:{app_id}"
                ),
            ]
        ]
    )


bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


@dp.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "Здравствуйте! Это бот Московского экономического института.\n\n"
        "Через мини-приложение вы можете подать заявку "
        "на дистанционные вступительные испытания."
    )
    await message.answer(text, reply_markup=main_menu())


@dp.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
    except Exception:
        await message.answer(
            "Не удалось обработать данные из мини-приложения. Попробуйте ещё раз."
        )
        return

    fio = (data.get("fio") or "").strip()
    birth = (data.get("birth") or "").strip()
    email = (data.get("email") or "").strip()
    doc = (data.get("doc") or "").strip()
    level = (data.get("level") or "").strip()
    direction = (data.get("direction") or "").strip()

    phone = str(message.from_user.id)  # пока как заглушка

    app_id = create_application(
        telegram_id=message.from_user.id,
        fio=fio,
        birth_date=birth,
        phone=phone,
        email=email,
        program_level=level,
        direction=direction,
        document_type=doc,
    )

    await message.answer(
        f"Ваша заявка №{app_id} отправлена в приёмную комиссию.\n\n"
        "После рассмотрения доступ к личному кабинету будет направлен сюда в чат.",
        reply_markup=main_menu(),
    )

    await notify_admin_new_application(app_id)


@dp.callback_query(F.data == "myapps")
async def cb_myapps(call: CallbackQuery):
    apps = get_user_applications(call.from_user.id)
    if not apps:
        await call.message.edit_text(
            "У вас пока нет поданных заявок.", reply_markup=main_menu()
        )
        return

    lines = []
    for app in apps:
        lines.append(
            f"№{app['id']}: {app['direction']} — {app['program_level']} — {app['status']}"
        )

    await call.message.edit_text("\n".join(lines), reply_markup=main_menu())


async def notify_admin_new_application(app_id: int):
    app = get_application(app_id)
    if not app:
        return

    text = (
        "📥 Новая заявка на вступительные испытания (дистанционно)\n\n"
        f"№ {app['id']}\n"
        f"Telegram ID: {app['telegram_id']}\n\n"
        f"ФИО: {app['fio']}\n"
        f"Дата рождения: {app['birth_date']}\n"
        f"Телефон: {app['phone']}\n"
        f"E-mail: {app['email']}\n"
        f"Документ об образовании: {app.get('document_type', '')}\n"
        f"Уровень образования: {app['program_level']}\n"
        f"Направление подготовки: {app['direction']}\n"
        f"Форма вступительного испытания: {app.get('exam_form', '')}\n"
        f"Статус: {app['status']}\n"
    )

    try:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=text,
            reply_markup=admin_decision_kb(app_id),
        )
    except Exception:
        pass


@dp.callback_query(F.data.startswith("approve:"))
async def cb_approve(call: CallbackQuery):
    if call.from_user.id != ADMIN_CHAT_ID:
        await call.answer("Недостаточно прав.")
        return

    app_id = int(call.data.split(":")[1])
    app = get_application(app_id)
    if not app:
        await call.answer("Заявка не найдена.")
        return

    set_status(app_id, "approved")

    try:
        await bot.send_message(
            chat_id=app["telegram_id"],
            text=(
                f"Ваша заявка №{app_id} одобрена.\n\n"
                "Вам будет направлен доступ к личному кабинету для сдачи "
                "вступительных испытаний."
            ),
        )
    except Exception:
        pass

    await call.answer("Заявка одобрена.")
    await call.message.edit_reply_markup(None)


@dp.callback_query(F.data.startswith("reject:"))
async def cb_reject(call: CallbackQuery):
    if call.from_user.id != ADMIN_CHAT_ID:
        await call.answer("Недостаточно прав.")
        return

    app_id = int(call.data.split(":")[1])
    app = get_application(app_id)
    if not app:
        await call.answer("Заявка не найдена.")
        return

    set_status(app_id, "rejected")

    try:
        await bot.send_message(
            chat_id=app["telegram_id"],
            text=(
                f"Ваша заявка №{app_id} отклонена.\n\n"
                "Причину отказа вы можете уточнить в приёмной комиссии."
            ),
        )
    except Exception:
        pass

    await call.answer("Заявка отклонена.")
    await call.message.edit_reply_markup(None)


async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())