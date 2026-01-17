from __future__ import annotations

from aiocryptopay import AioCryptoPay, Networks


class Payments:
    def __init__(self, token: str, network: str):
        network = (network or "mainnet").lower()
        net = Networks.MAIN_NET if network == "mainnet" else Networks.TEST_NET
        self.crypto = AioCryptoPay(token=token, network=net)

    async def start(self) -> None:
        await self.crypto.get_me()

    async def close(self) -> None:
        await self.crypto.close()

    async def create_invoice(self, asset: str, amount: float, description: str) -> tuple[int, str]:
        """Create invoice and return (invoice_id, pay_url).

        Different aiocryptopay versions expose invoice URL in different fields.
        We try the common ones in order.
        """
        inv = await self.crypto.create_invoice(asset=asset, amount=amount, description=description)

        pay_url = (
            getattr(inv, "bot_invoice_url", None)
            or getattr(inv, "pay_url", None)
            or getattr(inv, "mini_app_invoice_url", None)
        )
        if not pay_url:
            raise RuntimeError("Invoice created, but no pay URL returned by API")

        return int(inv.invoice_id), str(pay_url)

    async def get_invoices(self, invoice_ids: list[int]):
        return await self.crypto.get_invoices(invoice_ids=invoice_ids)

    async def create_check(self, asset: str, amount: float, description: str) -> tuple[int, str]:
        chk = await self.crypto.create_check(asset=asset, amount=amount, description=description)
        return int(chk.check_id), str(chk.bot_check_url)

    async def get_balance(self):
        """Return balances list from Crypto Pay API."""
        return await self.crypto.get_balance()

    async def get_available(self, asset: str) -> float:
        """Get available balance for a given asset (e.g., TON)."""
        balances = await self.get_balance()
        for b in balances:
            if getattr(b, "currency_code", None) == asset or getattr(b, "available", None) is not None:
                # aiocryptopay balance model usually has: currency_code, available
                if getattr(b, "currency_code", None) == asset:
                    return float(getattr(b, "available", 0) or 0)
        # Fallback: try attribute "name" used in some versions
        for b in balances:
            if getattr(b, "currency", None) == asset or getattr(b, "name", None) == asset:
                return float(getattr(b, "available", 0) or 0)
        return 0.0
