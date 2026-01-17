import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> set[int]:
    ids: set[int] = set()
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            continue
    return ids


@dataclass(frozen=True)
class Settings:
    bot_token: str
    crypto_pay_token: str
    crypto_pay_network: str
    admin_ids: set[int]
    support_username: str
    db_path: str
    ref_payout_min_ton: float
    ref_percent: float
    item_price_ton: float


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    crypto_pay_token = os.getenv("CRYPTO_PAY_TOKEN", "").strip()
    crypto_pay_network = os.getenv("CRYPTO_PAY_NETWORK", "mainnet").strip()
    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
    support_username = os.getenv("SUPPORT_USERNAME", "support").strip().lstrip("@")
    db_path = os.getenv("DB_PATH", "bot.db").strip()
    ref_payout_min_ton = float(os.getenv("REF_PAYOUT_MIN_TON", "3").strip())
    ref_percent = float(os.getenv("REF_PERCENT", "0.10").strip())
    item_price_ton = float(os.getenv("ITEM_PRICE_TON", "3.5").strip())

    if not bot_token:
        raise RuntimeError("BOT_TOKEN is required")
    if not crypto_pay_token:
        raise RuntimeError("CRYPTO_PAY_TOKEN is required")

    return Settings(
        bot_token=bot_token,
        crypto_pay_token=crypto_pay_token,
        crypto_pay_network=crypto_pay_network,
        admin_ids=admin_ids,
        support_username=support_username,
        db_path=db_path,
        ref_payout_min_ton=ref_payout_min_ton,
        ref_percent=ref_percent,
        item_price_ton=item_price_ton,
    )
