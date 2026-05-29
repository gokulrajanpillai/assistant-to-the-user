"""
ATHU Core - SQLite Interaction Logger
Logs all interactions, fitness check-ins, and trading audits.
"""

import aiosqlite
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/jarvis.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    user_input TEXT,
    intent TEXT,
    module TEXT,
    assistant_response TEXT,
    duration_ms INTEGER,
    llm_used TEXT,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS fitness_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    sleep_quality TEXT,
    workout_done INTEGER DEFAULT 0,
    workout_type TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS trading_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    strategy TEXT,
    ticker TEXT,
    action TEXT,
    quantity REAL,
    price REAL,
    confirmed INTEGER DEFAULT 0,
    dry_run INTEGER DEFAULT 1,
    result TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    due_date TEXT,
    completed_at TEXT,
    notes TEXT
);
"""


async def init_db():
    """Initialise the SQLite database and create tables if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def log_interaction(
    source: str,
    user_input: str | None = None,
    intent: str | None = None,
    module: str | None = None,
    response: str | None = None,
    duration_ms: int = 0,
    llm_used: str = "unknown",
    metadata: str = "{}",
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO interactions
               (timestamp, source, user_input, intent, module,
                assistant_response, duration_ms, llm_used, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.utcnow().isoformat(),
                source,
                user_input,
                intent,
                module,
                response,
                duration_ms,
                llm_used,
                metadata,
            ),
        )
        await db.commit()


async def log_fitness(
    sleep_quality: str | None = None,
    workout_done: bool = False,
    workout_type: str | None = None,
    notes: str | None = None,
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO fitness_logs
               (timestamp, sleep_quality, workout_done, workout_type, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (datetime.utcnow().isoformat(), sleep_quality, int(workout_done), workout_type, notes),
        )
        await db.commit()


async def log_trade(
    strategy: str,
    ticker: str,
    action: str,
    quantity: float,
    price: float,
    confirmed: bool,
    dry_run: bool,
    result: str = "",
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO trading_audit
               (timestamp, strategy, ticker, action, quantity,
                price, confirmed, dry_run, result)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.utcnow().isoformat(),
                strategy, ticker, action,
                quantity, price,
                int(confirmed), int(dry_run),
                result,
            ),
        )
        await db.commit()


async def get_recent_interactions(limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM interactions ORDER BY timestamp DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_fitness_summary(days: int = 7) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM fitness_logs ORDER BY timestamp DESC LIMIT ?", (days,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
