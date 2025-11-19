import sqlite3
from contextlib import closing

DB_NAME = "exam_bot.db"


def _get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _get_connection() as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                fio TEXT NOT NULL,
                birth_date TEXT,
                phone TEXT,
                email TEXT,
                document_type TEXT,
                program_level TEXT,
                direction TEXT,
                exam_form TEXT DEFAULT 'дистанционная',
                status TEXT DEFAULT 'new',
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        conn.commit()


def create_application(
    telegram_id: int,
    fio: str,
    birth_date: str,
    phone: str,
    email: str,
    program_level: str,
    direction: str,
    document_type: str | None = None,
) -> int:
    with _get_connection() as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            INSERT INTO applications (
                telegram_id, fio, birth_date, phone, email,
                document_type, program_level, direction
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_id,
                fio,
                birth_date,
                phone,
                email,
                document_type,
                program_level,
                direction,
            ),
        )
        conn.commit()
        return cur.lastrowid


def get_user_applications(telegram_id: int) -> list[dict]:
    with _get_connection() as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            SELECT id, telegram_id, fio, birth_date, phone, email,
                   document_type, program_level, direction,
                   exam_form, status, created_at
            FROM applications
            WHERE telegram_id = ?
            ORDER BY id DESC
            """,
            (telegram_id,),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def get_application(app_id: int) -> dict | None:
    with _get_connection() as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            SELECT id, telegram_id, fio, birth_date, phone, email,
                   document_type, program_level, direction,
                   exam_form, status, created_at
            FROM applications
            WHERE id = ?
            """,
            (app_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def set_status(app_id: int, status: str) -> None:
    with _get_connection() as conn, closing(conn.cursor()) as cur:
        cur.execute(
            "UPDATE applications SET status = ? WHERE id = ?",
            (status, app_id),
        )
        conn.commit()