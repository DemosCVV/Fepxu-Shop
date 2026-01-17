from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from ..keyboards import main_menu_kb

router = Router()


START_TEXT = (
    "✨ <b>Добро пожаловать в Fepxu Shop!</b>\n\n"
    "Здесь ты можешь безопасно купить цифровые товары и услуги, "
    "пополнить баланс криптовалютой и получить бонусы через реферальную систему.\n\n"
    "<i>Выбирай раздел в меню ниже 👇</i>"
)


@router.message(CommandStart())
async def cmd_start(message: Message, db, settings, bot):
    await db.upsert_user(message.from_user.id, message.from_user.username)

    # Referral binding: /start <ref_id>
    ref_id = None
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) == 2 and parts[1].isdigit():
            ref_id = int(parts[1])

    if ref_id:
        ok = await db.set_referrer_once(message.from_user.id, ref_id)
        if ok:
            # notify referrer
            try:
                await bot.send_message(
                    ref_id,
                    "🤝 По твоей ссылке зашёл новый пользователь!\n"
                    f"• Username: @{message.from_user.username or '—'}\n"
                    f"• ID: <code>{message.from_user.id}</code>\n\n"
                    "Теперь ты будешь получать процент от его покупок 💸",
                )
            except Exception:
                pass

    is_admin = message.from_user.id in settings.admin_ids
    await message.answer(START_TEXT, reply_markup=main_menu_kb(is_admin, settings.support_username))


@router.callback_query(F.data == "main")
async def back_main(call: CallbackQuery, settings):
    is_admin = call.from_user.id in settings.admin_ids
    await call.message.edit_text(START_TEXT, reply_markup=main_menu_kb(is_admin, settings.support_username))
    await call.answer()
