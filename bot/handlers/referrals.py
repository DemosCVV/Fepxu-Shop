from aiogram import Router, F
from aiogram.types import CallbackQuery

from ..keyboards import ref_kb

router = Router()


def _ref_text(bot_username: str, u, ref_percent: float) -> str:
    link = f"https://t.me/{bot_username}?start={u.user_id}"
    return (
        "🤝 <b>Реферальная система</b>\n\n"
        f"Твоя реф. ссылка: <code>{link}</code>\n"
        f"Реф. баланс: <b>{u.ref_balance_ton:.4f} TON</b>\n"
        f"Рефералов: <b>{u.referrals_count}</b>\n\n"
        f"За каждого реферала ты получаешь <b>{int(ref_percent*100)}%</b> от его покупок 💸"
    )


@router.callback_query(F.data == "ref")
async def ref(call: CallbackQuery, db, bot, settings):
    u = await db.get_user(call.from_user.id)
    me = await bot.get_me()
    await call.message.edit_text(_ref_text(me.username, u, settings.ref_percent), reply_markup=ref_kb())
    await call.answer()


@router.callback_query(F.data == "ref_withdraw")
async def ref_withdraw(call: CallbackQuery, db, settings, payments, bot):
    u = await db.get_user(call.from_user.id)
    if u.ref_balance_ton + 1e-9 < settings.ref_payout_min_ton:
        return await call.answer(
            f"Минимум для вывода: {settings.ref_payout_min_ton:.2f} TON",
            show_alert=True,
        )

    amount = float(u.ref_balance_ton)

    # Проверяем "казну" в Crypto Pay (доступный баланс TON).
    # Если казны не хватает — не списываем реф-баланс, уведомляем и админов, и пользователя.
    try:
        available = await payments.get_available("TON")
    except Exception:
        available = 0.0
    if available + 1e-9 < amount:
        await call.message.answer(
            "⚠️ Сейчас в казне недостаточно TON для автоматической выплаты. "
            f"С тобой свяжется @{settings.support_username}.",
        )
        for admin_id in settings.admin_ids:
            try:
                await bot.send_message(
                    admin_id,
                    "🏦 Недостаточно казны для реф. выплаты\n"
                    f"• Пользователь: @{call.from_user.username or '—'}\n"
                    f"• ID: <code>{call.from_user.id}</code>\n"
                    f"• Запрошено: <b>{amount:.4f} TON</b>\n"
                    f"• Доступно в Crypto Pay: <b>{available:.4f} TON</b>",
                )
            except Exception:
                pass
        await call.answer()
        return

    # Пытаемся создать чек в Crypto Pay
    try:
        _check_id, check_url = await payments.create_check(
            asset="TON",
            amount=round(amount, 4),
            description=f"Referral payout {call.from_user.id}",
        )
    except Exception:
        # если нет средств/ошибка — уведомляем пользователя и админов
        await call.message.answer(
            "⚠️ Сейчас не могу выдать выплату автоматически. "
            f"С тобой свяжется @{settings.support_username}.",
        )
        for admin_id in settings.admin_ids:
            try:
                await bot.send_message(
                    admin_id,
                    "⚠️ Запрос на вывод реф. баланса (авто-выплата не прошла)\n"
                    f"• Пользователь: @{call.from_user.username or '—'}\n"
                    f"• ID: <code>{call.from_user.id}</code>\n"
                    f"• Сумма: <b>{amount:.4f} TON</b>",
                )
            except Exception:
                pass
        await call.answer()
        return

    # Списываем реф баланс и выдаём чек
    await db.deduct_ref_balance(call.from_user.id, amount)
    await call.message.answer(
        "✅ <b>Выплата сформирована!</b>\n\n"
        f"Сумма: <b>{amount:.4f} TON</b>\n"
        f"Чек: {check_url}",
        disable_web_page_preview=True,
    )
    await call.answer()
