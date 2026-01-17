import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import load_settings
from .db import Database
from .payments import Payments

from .handlers import start, profile, catalog, referrals, admin


async def invoice_watcher(dp: Dispatcher):
    """Periodically checks active invoices and credits balances when paid."""
    db: Database = dp.workflow_data["db"]
    payments: Payments = dp.workflow_data["payments"]
    bot: Bot = dp.workflow_data["bot"]

    while True:
        try:
            pending = await db.get_pending_invoices(limit=50)
            if pending:
                invoice_ids = [inv_id for _, inv_id, _ in pending]
                invoices = await payments.get_invoices(invoice_ids)
                by_id = {int(i.invoice_id): i for i in invoices}

                for user_id, inv_id, amount_ton in pending:
                    inv = by_id.get(inv_id)
                    if not inv:
                        continue
                    status = getattr(inv, "status", "")
                    if status == "paid":
                        await db.update_invoice_status(inv_id, "paid")
                        await db.add_balance(user_id, float(amount_ton))
                        try:
                            await bot.send_message(
                                user_id,
                                "✅ <b>Платёж получен!</b>\n\n"
                                f"На баланс начислено: <b>{amount_ton:.4f} TON</b>",
                            )
                        except Exception:
                            pass
                    elif status in {"expired", "cancelled"}:
                        await db.update_invoice_status(inv_id, status)
        except Exception:
            logging.exception("Invoice watcher error")

        await asyncio.sleep(15)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()

    # aiogram >= 3.7.0: parse_mode is set via DefaultBotProperties
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    db = Database(settings.db_path)
    await db.init()

    payments = Payments(settings.crypto_pay_token, settings.crypto_pay_network)
    await payments.start()

    # Dependency injection
    dp.workflow_data.update({
        "bot": bot,
        "settings": settings,
        "db": db,
        "payments": payments,
    })

    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(catalog.router)
    dp.include_router(referrals.router)
    dp.include_router(admin.router)

    watcher_task = asyncio.create_task(invoice_watcher(dp))
    try:
        await dp.start_polling(bot)
    finally:
        watcher_task.cancel()
        await payments.close()
        await bot.session.close()


"""Bot bootstrap.

`main()` is intentionally not auto-run so you can choose your own entrypoint.
Use the repository root `main.py` to start the bot.
"""
