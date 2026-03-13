import asyncpg
import os
from config import Config
from utils.logger import setup_logger

logger = setup_logger("database")

# Global connection pool
_pool: asyncpg.Pool = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=Config.DATABASE_URL,
            min_size=1,
            max_size=5,
        )
        logger.info("Database connection pool created")
    return _pool


async def close_pool():
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


async def init_db():
    """Initialize the database and create tables."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                language TEXT DEFAULT 'vi',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                oil_type TEXT NOT NULL,
                condition TEXT NOT NULL,
                target_price DOUBLE PRECISION NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                triggered_at TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS vn_alert_users (
                chat_id BIGINT PRIMARY KEY,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_alert_users (
                chat_id BIGINT PRIMARY KEY,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS volatility_alert_users (
                chat_id BIGINT PRIMARY KEY,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id)
            )
        """)

        # ─── Gold tables ────────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS gold_prices_vn (
                id SERIAL PRIMARY KEY,
                brand TEXT NOT NULL,
                price_type TEXT NOT NULL,
                price_per_chi BIGINT NOT NULL,
                source TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS gold_alerts (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                symbol TEXT NOT NULL,
                condition TEXT NOT NULL,
                target_price DOUBLE PRECISION NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                triggered_at TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id)
            )
        """)

        # ─── Silver tables ───────────────────────────────────
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS silver_prices_vn (
                id SERIAL PRIMARY KEY,
                brand TEXT NOT NULL,
                price_type TEXT NOT NULL,
                price_per_chi BIGINT NOT NULL,
                source TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS silver_alerts (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                symbol TEXT NOT NULL,
                condition TEXT NOT NULL,
                target_price DOUBLE PRECISION NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                triggered_at TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id)
            )
        """)

    logger.info("Database initialized successfully")


async def upsert_user(chat_id: int, username: str = None, first_name: str = None):
    """Insert or update a user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (chat_id, username, first_name) 
            VALUES ($1, $2, $3)
            ON CONFLICT(chat_id) DO UPDATE SET 
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name
            """,
            chat_id, username, first_name,
        )


async def add_alert(chat_id: int, oil_type: str, condition: str, target_price: float) -> int:
    """Add a new price alert. Returns the alert ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO alerts (chat_id, oil_type, condition, target_price)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            chat_id, oil_type.upper(), condition.lower(), target_price,
        )
        return row["id"]


async def get_user_alerts(chat_id: int) -> list:
    """Get all active alerts for a user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, oil_type, condition, target_price, created_at
            FROM alerts 
            WHERE chat_id = $1 AND is_active = 1
            ORDER BY created_at DESC
            """,
            chat_id,
        )
        return [dict(row) for row in rows]


async def get_all_active_alerts() -> list:
    """Get all active alerts from all users."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, chat_id, oil_type, condition, target_price
            FROM alerts 
            WHERE is_active = 1
            """,
        )
        return [dict(row) for row in rows]


async def deactivate_alert(alert_id: int):
    """Deactivate an alert after it has been triggered."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE alerts 
            SET is_active = 0, triggered_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            alert_id,
        )


async def delete_alert(alert_id: int, chat_id: int) -> bool:
    """Delete an alert. Returns True if deleted."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM alerts WHERE id = $1 AND chat_id = $2",
            alert_id, chat_id,
        )
        return result == "DELETE 1"


# ─── VN Alert Subscriptions ─────────────────────────────────

async def subscribe_vn_alert(chat_id: int) -> bool:
    """Subscribe user to VN price change alerts. Returns True if newly subscribed."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO vn_alert_users (chat_id, enabled)
            VALUES ($1, 1)
            ON CONFLICT(chat_id) DO UPDATE SET enabled = 1
            """,
            chat_id,
        )
        return True


async def unsubscribe_vn_alert(chat_id: int) -> bool:
    """Unsubscribe user from VN price change alerts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE vn_alert_users SET enabled = 0 WHERE chat_id = $1",
            chat_id,
        )
        return result != "UPDATE 0"


async def get_all_vn_alert_users() -> list:
    """Get all users subscribed to VN price change alerts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT chat_id FROM vn_alert_users WHERE enabled = 1"
        )
        return [dict(row) for row in rows]


async def is_vn_alert_subscribed(chat_id: int) -> bool:
    """Check if a user is subscribed to VN alerts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT enabled FROM vn_alert_users WHERE chat_id = $1 AND enabled = 1",
            chat_id,
        )
        return row is not None


# ─── Daily Alert Subscriptions ─────────────────────────────────

async def subscribe_daily_alert(chat_id: int) -> bool:
    """Subscribe user to daily 7AM price reports."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO daily_alert_users (chat_id, enabled)
            VALUES ($1, 1)
            ON CONFLICT(chat_id) DO UPDATE SET enabled = 1
            """,
            chat_id,
        )
        return True

async def unsubscribe_daily_alert(chat_id: int) -> bool:
    """Unsubscribe user from daily price reports."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE daily_alert_users SET enabled = 0 WHERE chat_id = $1",
            chat_id,
        )
        return result != "UPDATE 0"

async def get_all_daily_alert_users() -> list:
    """Get all users subscribed to daily price reports."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT chat_id FROM daily_alert_users WHERE enabled = 1"
        )
        return [dict(row) for row in rows]

async def is_daily_alert_subscribed(chat_id: int) -> bool:
    """Check if a user is subscribed to daily alerts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT enabled FROM daily_alert_users WHERE chat_id = $1 AND enabled = 1",
            chat_id,
        )
        return row is not None


# ─── Volatility Alert Subscriptions ────────────────────────────

async def subscribe_volatility_alert(chat_id: int) -> bool:
    """Subscribe user to volatility alerts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO volatility_alert_users (chat_id, enabled)
            VALUES ($1, 1)
            ON CONFLICT(chat_id) DO UPDATE SET enabled = 1
            """,
            chat_id,
        )
        return True

async def unsubscribe_volatility_alert(chat_id: int) -> bool:
    """Unsubscribe user from volatility alerts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE volatility_alert_users SET enabled = 0 WHERE chat_id = $1",
            chat_id,
        )
        return result != "UPDATE 0"

async def get_all_volatility_alert_users() -> list:
    """Get all users subscribed to volatility alerts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT chat_id FROM volatility_alert_users WHERE enabled = 1"
        )
        return [dict(row) for row in rows]

async def is_volatility_alert_subscribed(chat_id: int) -> bool:
    """Check if a user is subscribed to volatility alerts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT enabled FROM volatility_alert_users WHERE chat_id = $1 AND enabled = 1",
            chat_id,
        )
        return row is not None


# ─── Gold VN Price History ──────────────────────────────────

async def insert_gold_vn_price(brand: str, price_type: str, price_per_chi: int, source: str = ""):
    """Insert a gold VN price snapshot."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO gold_prices_vn (brand, price_type, price_per_chi, source)
            VALUES ($1, $2, $3, $4)
            """,
            brand, price_type, price_per_chi, source,
        )


async def get_gold_vn_history(brand: str, price_type: str, days: int = 30) -> list:
    """Get gold VN price history for charting."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT price_per_chi, fetched_at
            FROM gold_prices_vn
            WHERE brand = $1 AND price_type = $2
              AND fetched_at >= CURRENT_TIMESTAMP - make_interval(days => $3)
            ORDER BY fetched_at ASC
            """,
            brand, price_type, days,
        )
        return [dict(row) for row in rows]


# ─── Gold Alerts ────────────────────────────────────────────

async def add_gold_alert(chat_id: int, symbol: str, condition: str, target_price: float) -> int:
    """Add a new gold price alert. Returns the alert ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO gold_alerts (chat_id, symbol, condition, target_price)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            chat_id, symbol.upper(), condition.lower(), target_price,
        )
        return row["id"]


async def get_user_gold_alerts(chat_id: int) -> list:
    """Get all active gold alerts for a user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, symbol, condition, target_price, created_at
            FROM gold_alerts
            WHERE chat_id = $1 AND is_active = 1
            ORDER BY created_at DESC
            """,
            chat_id,
        )
        return [dict(row) for row in rows]


async def get_all_active_gold_alerts() -> list:
    """Get all active gold alerts from all users."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, chat_id, symbol, condition, target_price FROM gold_alerts WHERE is_active = 1"
        )
        return [dict(row) for row in rows]


async def deactivate_gold_alert(alert_id: int):
    """Deactivate a gold alert after it has been triggered."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE gold_alerts SET is_active = 0, triggered_at = CURRENT_TIMESTAMP WHERE id = $1",
            alert_id,
        )


async def delete_gold_alert(alert_id: int, chat_id: int) -> bool:
    """Delete a gold alert. Returns True if deleted."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM gold_alerts WHERE id = $1 AND chat_id = $2",
            alert_id, chat_id,
        )
        return result == "DELETE 1"


# ─── Silver VN Price History ─────────────────────────────────

async def insert_silver_vn_price(brand: str, price_type: str, price_per_chi: int, source: str = ""):
    """Insert a silver VN price snapshot."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO silver_prices_vn (brand, price_type, price_per_chi, source)
            VALUES ($1, $2, $3, $4)
            """,
            brand, price_type, price_per_chi, source,
        )


async def get_silver_vn_history(brand: str, price_type: str, days: int = 30) -> list:
    """Get silver VN price history for charting."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT price_per_chi, fetched_at
            FROM silver_prices_vn
            WHERE brand = $1 AND price_type = $2
              AND fetched_at >= CURRENT_TIMESTAMP - make_interval(days => $3)
            ORDER BY fetched_at ASC
            """,
            brand, price_type, days,
        )
        return [dict(row) for row in rows]


# ─── Silver Alerts ───────────────────────────────────────────

async def add_silver_alert(chat_id: int, symbol: str, condition: str, target_price: float) -> int:
    """Add a new silver price alert. Returns the alert ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO silver_alerts (chat_id, symbol, condition, target_price)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            chat_id, symbol.upper(), condition.lower(), target_price,
        )
        return row["id"]


async def get_user_silver_alerts(chat_id: int) -> list:
    """Get all active silver alerts for a user."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, symbol, condition, target_price, created_at
            FROM silver_alerts
            WHERE chat_id = $1 AND is_active = 1
            ORDER BY created_at DESC
            """,
            chat_id,
        )
        return [dict(row) for row in rows]


async def get_all_active_silver_alerts() -> list:
    """Get all active silver alerts from all users."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, chat_id, symbol, condition, target_price FROM silver_alerts WHERE is_active = 1"
        )
        return [dict(row) for row in rows]


async def deactivate_silver_alert(alert_id: int):
    """Deactivate a silver alert after it has been triggered."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE silver_alerts SET is_active = 0, triggered_at = CURRENT_TIMESTAMP WHERE id = $1",
            alert_id,
        )


async def delete_silver_alert(alert_id: int, chat_id: int) -> bool:
    """Delete a silver alert. Returns True if deleted."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM silver_alerts WHERE id = $1 AND chat_id = $2",
            alert_id, chat_id,
        )
        return result == "DELETE 1"
