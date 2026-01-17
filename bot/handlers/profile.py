from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from ..keyboards import profile_kb, pay_invoice_kb
from ..states import TopUp

router = Router()


def _profile_text(u) -> str:
    return (
        "👤 <b>Твой профиль</b>\n\n"
        f"• Username: @{u.username or '—'}\n"
        f"• ID: <code>{u.user_id}</code>\n"
        f"• Баланс: <b>{u.balance_ton:.4f} TON</b>\n"
    )


@router.callback_query(F.data == "profile")
async def profile(call: CallbackQuery, db):
    u = await db.get_user(call.from_user.id)
    await call.message.edit_text(_profile_text(u), reply_markup=profile_kb())
    await call.answer()


@router.callback_query(F.data == "topup")
async def topup_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(TopUp.waiting_amount)
    await call.message.edit_text(
        "💎 <b>Пополнение баланса (TON)</b>\n\n"
        "✍️ Введи сумму в TON, которую хочешь пополнить.\n"
        "Пример: <code>3.5</code> или <code>10</code>",
    )
    await call.answer()


@router.message(TopUp.waiting_amount)
async def enter_amount(message: Message, state: FSMContext, db, payments, settings):
    raw = (message.text or "").replace(",", ".").strip()
    try:
        amount = float(raw)
    except Exception:
        return await message.answer("❌ Это не похоже на число. Попробуй ещё раз.")

    if amount <= 0:
        return await message.answer("❌ Сумма должна быть больше 0.")

    asset = "TON"
    amount_ton = amount

    desc = f"Topup {message.from_user.id}"
    try:
        invoice_id, pay_url = await payments.create_invoice(asset=asset, amount=amount, description=desc)
    except Exception:
        return await message.answer(
            "⚠️ Не удалось создать счёт на оплату.\n\n"
            "Проверь, что:\n"
            "1) В .env указан верный <b>CRYPTO_PAY_TOKEN</b>\n"
            "2) Верно указан <b>CRYPTO_PAY_NETWORK</b> (mainnet/testnet)\n"
            "3) Crypto Pay API включён в приложении @CryptoBot\n"
            "\nПосле исправления попробуй ещё раз."
        )
    await db.add_invoice(message.from_user.id, invoice_id, asset, amount, amount_ton, status="active")

    await message.answer(
        "🧾 <b>Счёт на пополнение создан</b>\n\n"
        f"Сумма: <b>{amount_ton:.4f} TON</b>\n"
        "Нажми кнопку ниже, чтобы оплатить. После оплаты баланс зачислится автоматически ✅",
        reply_markup=pay_invoice_kb(pay_url, back_callback="profile"),
    )
    await state.clear()
