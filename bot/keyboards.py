from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb(is_admin: bool, support_username: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="👤 Мой профиль", callback_data="profile")
    b.button(text="🛍️ Каталог", callback_data="catalog")
    b.button(text="🤝 Реф система", callback_data="ref")
    b.button(text="🆘 Поддержка", url=f"https://t.me/{support_username}")
    if is_admin:
        b.button(text="⚙️ Админка", callback_data="admin")
    b.adjust(2, 2, 1)
    return b.as_markup()


def back_to_main_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Назад", callback_data="main")
    return b.as_markup()


def pay_invoice_kb(pay_url: str, back_callback: str = "profile") -> InlineKeyboardMarkup:
    """Button that opens CryptoBot invoice + back button."""
    b = InlineKeyboardBuilder()
    b.button(text="✅ Оплатить", url=pay_url)
    b.button(text="⬅️ Назад", callback_data=back_callback)
    b.adjust(1)
    return b.as_markup()


def profile_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💎 Пополнить баланс", callback_data="topup")
    b.button(text="⬅️ Назад", callback_data="main")
    b.adjust(1)
    return b.as_markup()


def catalog_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📱 Аккаунты", callback_data="accounts")
    b.button(text="⬅️ Назад", callback_data="main")
    b.adjust(1)
    return b.as_markup()


def accounts_kb(price_ton: float) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=f"🛒 Купить за {price_ton:.2f} TON", callback_data="buy:accounts")
    b.button(text="⬅️ Назад", callback_data="catalog")
    b.adjust(1)
    return b.as_markup()


def ref_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="💸 Вывести реф. баланс", callback_data="ref_withdraw")
    b.button(text="⬅️ Назад", callback_data="main")
    b.adjust(1)
    return b.as_markup()


def admin_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📣 Расссылка", callback_data="admin_broadcast")
    b.button(text="➕ Выдать баланс", callback_data="admin_grant")
    b.button(text="📊 Статистика", callback_data="admin_stats")
    b.button(text="🏦 Казна (реф. выплаты)", callback_data="admin_treasury")
    b.button(text="⬅️ Назад", callback_data="main")
    b.adjust(2, 2, 1)
    return b.as_markup()
