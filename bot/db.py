import aiosqlite
from dataclasses import dataclass
from datetime import datetime


def utcnow() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


@dataclass
class User:
    user_id: int
    username: str | None
    balance_ton: float
    referrer_id: int | None
    ref_balance_ton: float
    referrals_count: int


class Database:
    def __init__(self, path: str):
        self.path = path

    async def init(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    balance_ton REAL NOT NULL DEFAULT 0,
                    referrer_id INTEGER,
                    ref_balance_ton REAL NOT NULL DEFAULT 0,
                    referrals_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    invoice_id INTEGER NOT NULL,
                    asset TEXT NOT NULL,
                    amount REAL NOT NULL,
                    amount_ton REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(invoice_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    item_key TEXT NOT NULL,
                    price_ton REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            await db.commit()

    async def upsert_user(self, user_id: int, username: str | None) -> None:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
            row = await cur.fetchone()
            if row is None:
                await db.execute(
                    "INSERT INTO users(user_id, username, created_at) VALUES(?,?,?)",
                    (user_id, username, utcnow()),
                )
            else:
                await db.execute(
                    "UPDATE users SET username=? WHERE user_id=?",
                    (username, user_id),
                )
            await db.commit()

    async def set_referrer_once(self, user_id: int, referrer_id: int) -> bool:
        """Bind referrer only once. Returns True if set, False if already set/invalid."""
        if user_id == referrer_id:
            return False
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT referrer_id FROM users WHERE user_id=?",
                (user_id,),
            )
            row = await cur.fetchone()
            if row is None:
                return False
            if row[0] is not None:
                return False
            # Ensure referrer exists
            cur2 = await db.execute("SELECT user_id FROM users WHERE user_id=?", (referrer_id,))
            if await cur2.fetchone() is None:
                return False
            await db.execute("UPDATE users SET referrer_id=? WHERE user_id=?", (referrer_id, user_id))
            await db.execute("UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id=?", (referrer_id,))
            await db.commit()
            return True

    async def get_user(self, user_id: int) -> User | None:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT user_id, username, balance_ton, referrer_id, ref_balance_ton, referrals_count FROM users WHERE user_id=?",
                (user_id,),
            )
            row = await cur.fetchone()
            if row is None:
                return None
            return User(
                user_id=row[0],
                username=row[1],
                balance_ton=float(row[2] or 0),
                referrer_id=row[3],
                ref_balance_ton=float(row[4] or 0),
                referrals_count=int(row[5] or 0),
            )

    async def get_user_by_username(self, username: str) -> User | None:
        """Find user by username (case-insensitive). Username should be without '@'."""
        username = (username or "").strip().lstrip("@").lower()
        if not username:
            return None
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT user_id, username, balance_ton, referrer_id, ref_balance_ton, referrals_count FROM users WHERE LOWER(username)=? LIMIT 1",
                (username,),
            )
            row = await cur.fetchone()
            if row is None:
                return None
            return User(
                user_id=row[0],
                username=row[1],
                balance_ton=float(row[2] or 0),
                referrer_id=row[3],
                ref_balance_ton=float(row[4] or 0),
                referrals_count=int(row[5] or 0),
            )

    async def add_balance(self, user_id: int, ton: float) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET balance_ton = balance_ton + ? WHERE user_id=?", (ton, user_id))
            await db.commit()

    async def deduct_balance(self, user_id: int, ton: float) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT balance_ton FROM users WHERE user_id=?", (user_id,))
            row = await cur.fetchone()
            if row is None:
                return False
            bal = float(row[0] or 0)
            if bal + 1e-9 < ton:
                return False
            await db.execute("UPDATE users SET balance_ton = balance_ton - ? WHERE user_id=?", (ton, user_id))
            await db.commit()
            return True

    async def add_ref_balance(self, user_id: int, ton: float) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET ref_balance_ton = ref_balance_ton + ? WHERE user_id=?", (ton, user_id))
            await db.commit()

    async def deduct_ref_balance(self, user_id: int, ton: float) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT ref_balance_ton FROM users WHERE user_id=?", (user_id,))
            row = await cur.fetchone()
            if row is None:
                return False
            bal = float(row[0] or 0)
            if bal + 1e-9 < ton:
                return False
            await db.execute("UPDATE users SET ref_balance_ton = ref_balance_ton - ? WHERE user_id=?", (ton, user_id))
            await db.commit()
            return True

    async def add_invoice(self, user_id: int, invoice_id: int, asset: str, amount: float, amount_ton: float, status: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO invoices(user_id, invoice_id, asset, amount, amount_ton, status, created_at) VALUES(?,?,?,?,?,?,?)",
                (user_id, invoice_id, asset, amount, amount_ton, status, utcnow()),
            )
            await db.commit()

    async def update_invoice_status(self, invoice_id: int, status: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE invoices SET status=? WHERE invoice_id=?", (status, invoice_id))
            await db.commit()

    async def get_pending_invoices(self, limit: int = 50) -> list[tuple[int, int, float]]:
        """Returns (user_id, invoice_id, amount_ton)"""
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "SELECT user_id, invoice_id, amount_ton FROM invoices WHERE status='active' ORDER BY id ASC LIMIT ?",
                (limit,),
            )
            rows = await cur.fetchall()
            return [(int(r[0]), int(r[1]), float(r[2] or 0)) for r in rows]

    async def add_order(self, user_id: int, item_key: str, price_ton: float) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO orders(user_id, item_key, price_ton, created_at) VALUES(?,?,?,?)",
                (user_id, item_key, price_ton, utcnow()),
            )
            await db.commit()

    async def get_stats(self) -> dict:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT COUNT(*) FROM users")
            users = int((await cur.fetchone())[0])
            cur = await db.execute("SELECT COUNT(*) FROM orders")
            orders = int((await cur.fetchone())[0])
            cur = await db.execute("SELECT IFNULL(SUM(price_ton),0) FROM orders")
            revenue_ton = float((await cur.fetchone())[0])
            return {"users": users, "orders": orders, "revenue_ton": revenue_ton}
