from aiogram import Router, F
from aiogram.types import CallbackQuery

from ..keyboards import catalog_kb, accounts_kb

router = Router()

CATALOG_TEXT = (
    "🛍️ <b>Каталог</b>\n\n"
    "Здесь собраны товары и услуги. Выбирай категорию ниже 👇"
)

ACCOUNTS_TEXT = (
    "📱 <b>Аккаунты</b>\n\n"
    "• Тип: <b>Физ</b>\n"
    "• Регион: <b>Ру</b>\n"
    "• Выдача: <b>после покупки с вами свяжется поддержка</b>\n\n"
    "Цена: <b>{price:.2f} TON</b>"
)


@router.callback_query(F.data == "catalog")
async def catalog(call: CallbackQuery):
    await call.message.edit_text(CATALOG_TEXT, reply_markup=catalog_kb())
    await call.answer()


@router.callback_query(F.data == "accounts")
async def accounts(call: CallbackQuery, settings):
    await call.message.edit_text(
        ACCOUNTS_TEXT.format(price=float(settings.item_price_ton)),
        reply_markup=accounts_kb(float(settings.item_price_ton)),
    )
    await call.answer()


@router.callback_query(F.data.startswith("buy:"))
async def buy_item(call: CallbackQuery, db, settings, bot, payments):
    item_key = call.data.split(":", 1)[1]
    price_ton = settings.item_price_ton

    if item_key != "accounts":
        return await call.answer("Неизвестный товар", show_alert=True)

    ok = await db.deduct_balance(call.from_user.id, price_ton)
    if not ok:
        return await call.answer("Недостаточно средств на балансе", show_alert=True)

    await db.add_order(call.from_user.id, item_key, price_ton)

    # Реферальная комиссия (10% по умолчанию), начисляем в TON
    buyer = await db.get_user(call.from_user.id)
    if buyer and buyer.referrer_id:
        commission_ton = float(price_ton) * float(settings.ref_percent)
        if commission_ton > 0:
            await db.add_ref_balance(buyer.referrer_id, commission_ton)
            # уведомим реферера
            try:
                await bot.send_message(
                    buyer.referrer_id,
                    "💸 Начислена реф. комиссия!\n"
                    f"• Покупка реферала: <code>{call.from_user.id}</code>\n"
                    f"• Комиссия: <b>{commission_ton:.4f} TON</b>",
                )
            except Exception:
                pass

    # Сообщение покупателю
    await call.message.edit_text(
        "✅ <b>Покупка успешна!</b>\n\n"
        f"С вами свяжется поддержка: @{settings.support_username}\n"
        "(обычно в течение короткого времени).",
        reply_markup=None,
    )

    # Уведомление админу
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                "🛒 Новая покупка\n"
                f"• Покупатель: @{call.from_user.username or '—'}\n"
                f"• ID: <code>{call.from_user.id}</code>\n"
                f"• Товар: {item_key}\n"
                f"• Сумма: {price_ton:.2f} TON",
            )
        except Exception:
            pass

    await call.answer()
