import aiosqlite
from config import Config
from utils.logger import setup_logger

logger = setup_logger("database")


async def init_db():
    """Initialize the database and create tables."""
    async with aiosqlite.connect(Config.DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                language TEXT DEFAULT 'vi',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                oil_type TEXT NOT NULL,
                condition TEXT NOT NULL,
                target_price REAL NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                triggered_at TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id)
            )
        """)

        await db.commit()
        logger.info("Database initialized successfully")


async def upsert_user(chat_id: int, username: str = None, first_name: str = None):
    """Insert or update a user."""
    async with aiosqlite.connect(Config.DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (chat_id, username, first_name) 
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET 
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (chat_id, username, first_name),
        )
        await db.commit()


async def add_alert(chat_id: int, oil_type: str, condition: str, target_price: float) -> int:
    """Add a new price alert. Returns the alert ID."""
    async with aiosqlite.connect(Config.DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO alerts (chat_id, oil_type, condition, target_price)
            VALUES (?, ?, ?, ?)
            """,
            (chat_id, oil_type.upper(), condition.lower(), target_price),
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_alerts(chat_id: int) -> list:
    """Get all active alerts for a user."""
    async with aiosqlite.connect(Config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, oil_type, condition, target_price, created_at
            FROM alerts 
            WHERE chat_id = ? AND is_active = 1
            ORDER BY created_at DESC
            """,
            (chat_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_all_active_alerts() -> list:
    """Get all active alerts from all users."""
    async with aiosqlite.connect(Config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, chat_id, oil_type, condition, target_price
            FROM alerts 
            WHERE is_active = 1
            """,
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def deactivate_alert(alert_id: int):
    """Deactivate an alert after it has been triggered."""
    async with aiosqlite.connect(Config.DB_PATH) as db:
        await db.execute(
            """
            UPDATE alerts 
            SET is_active = 0, triggered_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (alert_id,),
        )
        await db.commit()


async def delete_alert(alert_id: int, chat_id: int) -> bool:
    """Delete an alert. Returns True if deleted."""
    async with aiosqlite.connect(Config.DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM alerts WHERE id = ? AND chat_id = ?",
            (alert_id, chat_id),
        )
        await db.commit()
        return cursor.rowcount > 0
