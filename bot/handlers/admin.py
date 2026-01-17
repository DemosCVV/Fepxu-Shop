from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from ..keyboards import admin_kb
from ..states import AdminBroadcast, AdminGrant

router = Router()


def _is_admin(user_id: int, settings) -> bool:
    return user_id in settings.admin_ids


@router.callback_query(F.data == "admin")
async def admin_menu(call: CallbackQuery, settings):
    if not _is_admin(call.from_user.id, settings):
        return await call.answer("Нет доступа", show_alert=True)
    await call.message.edit_text("⚙️ <b>Админка</b>", reply_markup=admin_kb())
    await call.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery, settings, db):
    if not _is_admin(call.from_user.id, settings):
        return await call.answer("Нет доступа", show_alert=True)
    stats = await db.get_stats()
    await call.message.answer(
        "📊 <b>Статистика</b>\n\n"
        f"Пользователей: <b>{stats['users']}</b>\n"
        f"Покупок: <b>{stats['orders']}</b>\n"
        f"Оборот: <b>{stats['revenue_ton']:.4f} TON</b>",
    )
    await call.answer()


@router.callback_query(F.data == "admin_treasury")
async def admin_treasury(call: CallbackQuery, settings, payments):
    """Shows current Crypto Pay balances for payouts (TON-only)."""
    if not _is_admin(call.from_user.id, settings):
        return await call.answer("Нет доступа", show_alert=True)

    try:
        ton_available = await payments.get_available("TON")
    except Exception:
        ton_available = 0.0

    await call.message.answer(
        "🏦 <b>Казна для реф. выплат</b>\n\n"
        f"Доступно TON в Crypto Pay: <b>{ton_available:.4f} TON</b>\n\n"
        "Чтобы пополнить казну:\n"
        "1) Открой @CryptoBot → Crypto Pay\n"
        "2) Выбери ваше приложение\n"
        "3) Пополни баланс TON\n\n"
        "После пополнения пользователи смогут получать чеки автоматически."
    )
    await call.answer()


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(call: CallbackQuery, state: FSMContext, settings):
    if not _is_admin(call.from_user.id, settings):
        return await call.answer("Нет доступа", show_alert=True)
    await state.set_state(AdminBroadcast.waiting_text)
    await call.message.answer("📣 Отправь текст рассылки одним сообщением.")
    await call.answer()


@router.message(AdminBroadcast.waiting_text)
async def admin_broadcast_send(message: Message, state: FSMContext, settings, db, bot):
    if not _is_admin(message.from_user.id, settings):
        return
    text = message.text or ""
    if not text.strip():
        return await message.answer("Пустой текст")

    # простая рассылка: отправляем всем пользователям
    # (для больших баз лучше делать пачками/очередью)
    import aiosqlite
    sent = 0
    failed = 0
    async with aiosqlite.connect(settings.db_path) as conn:
        cur = await conn.execute("SELECT user_id FROM users")
        rows = await cur.fetchall()

    for (uid,) in rows:
        try:
            await bot.send_message(int(uid), text)
            sent += 1
        except Exception:
            failed += 1

    await message.answer(f"✅ Готово. Отправлено: {sent}, ошибок: {failed}")
    await state.clear()


@router.callback_query(F.data == "admin_grant")
async def admin_grant_start(call: CallbackQuery, state: FSMContext, settings):
    if not _is_admin(call.from_user.id, settings):
        return await call.answer("Нет доступа", show_alert=True)
    await state.set_state(AdminGrant.waiting_user_id)
    await call.message.answer(
        "➕ <b>Выдача баланса</b>\n\n"
        "Отправь <b>ID</b> пользователя или его <b>@username</b>.\n"
        "Примеры: <code>123456789</code> или <code>@nickname</code>"
    )
    await call.answer()


@router.message(AdminGrant.waiting_user_id)
async def admin_grant_uid(message: Message, state: FSMContext, settings, db):
    if not _is_admin(message.from_user.id, settings):
        return
    raw = (message.text or "").strip()
    uid = None
    if raw.isdigit():
        uid = int(raw)
        u = await db.get_user(uid)
    else:
        u = await db.get_user_by_username(raw)
        uid = u.user_id if u else None

    if not u:
        return await message.answer(
            "Пользователь не найден.\n\n"
            "Он должен хотя бы один раз нажать /start, чтобы бот увидел его username/ID."
        )
    await state.update_data(uid=uid)
    await state.set_state(AdminGrant.waiting_amount)
    await message.answer(
        "Сколько <b>TON</b> начислить?\n"
        "Пример: <code>1.5</code>"
    )


@router.message(AdminGrant.waiting_amount)
async def admin_grant_amount(message: Message, state: FSMContext, settings, db, bot):
    if not _is_admin(message.from_user.id, settings):
        return
    raw = (message.text or "").replace(",", ".").strip()
    try:
        amount = float(raw)
    except Exception:
        return await message.answer("Это не число")
    if amount <= 0:
        return await message.answer("Сумма должна быть > 0")

    data = await state.get_data()
    uid = int(data["uid"])
    await db.add_balance(uid, amount)
    await message.answer(f"✅ Начислено {amount:.4f} TON пользователю <code>{uid}</code>")
    try:
        await bot.send_message(uid, f"🎁 Тебе начислено <b>{amount:.4f} TON</b> администратором.")
    except Exception:
        pass
    await state.clear()
