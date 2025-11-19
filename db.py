# db.py
import sqlite3
from typing import List, Dict, Any

from config import DB_PATH


def _get_connection():
    """
    Открываем новое соединение к БД.
    Используем отдельное соединение на каждый запрос,
    чтобы не ловить проблем в асинхронном окружении.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # чтобы получать dict-подобные строки
    return conn


def init_db() -> None:
    """
    Создаёт таблицу заявок, если её ещё нет.
    """
    conn = _get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                username        TEXT,
                fio             TEXT,
                birth           TEXT,
                email           TEXT,
                doc_type        TEXT,
                program_level   TEXT,
                direction       TEXT,
                status          TEXT DEFAULT 'Новая',
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def create_application(
    user_id: int,
    username: str,
    fio: str,
    birth: str,
    email: str,
    doc_type: str,
    program_level: str,
    direction: str,
) -> int:
    """
    Создаёт новую заявку и возвращает её ID.
    """
    conn = _get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO applications (
                user_id,
                username,
                fio,
                birth,
                email,
                doc_type,
                program_level,
                direction,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Новая')
            """,
            (user_id, username, fio, birth, email, doc_type, program_level, direction),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user_applications(user_id: int) -> List[Dict[str, Any]]:
    """
    Возвращает список заявок пользователя.
    Используется для кнопки «Мои заявки».
    """
    conn = _get_connection()
    try:
        cur = conn.execute(
            """
            SELECT
                id,
                direction,
                program_level,
                status
            FROM applications
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
