"""
database.py  —  Secure SQLite layer for AI Attendance System.
All SQL uses parameterised statements (no string concatenation).
"""

import sqlite3
import os
import logging
from datetime import datetime, date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH  = BASE_DIR / "attendance.db"

logger = logging.getLogger(__name__)


# ── connection ─────────────────────────────────────────────────────────────────
def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    c.execute("PRAGMA journal_mode  = WAL")
    return c


# ── schema ─────────────────────────────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    TEXT    NOT NULL UNIQUE,
    name          TEXT    NOT NULL,
    department    TEXT    NOT NULL DEFAULT '',
    face_image    TEXT    NOT NULL DEFAULT '',
    encoding      BLOB    NOT NULL,
    registered_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS attendance (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    date       TEXT NOT NULL,
    time       TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'Present',
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    UNIQUE(student_id, date)
);
"""


def init_db():
    try:
        with _conn() as c:
            c.executescript(_SCHEMA)
        logger.info("DB ready → %s", DB_PATH)
    except sqlite3.Error as e:
        logger.error("init_db: %s", e)
        raise


# ── students ───────────────────────────────────────────────────────────────────
def add_student(student_id: str, name: str, department: str,
                face_image: str, encoding_bytes: bytes) -> bool:
    sql = """INSERT INTO students
             (student_id, name, department, face_image, encoding, registered_at)
             VALUES (?,?,?,?,?,?)"""
    try:
        with _conn() as c:
            c.execute(sql, (
                student_id, name, department,
                os.path.basename(face_image),   # strip path traversal
                encoding_bytes,
                datetime.now().isoformat(timespec="seconds"),
            ))
        logger.info("Registered: %s", student_id)
        return True
    except sqlite3.IntegrityError:
        logger.warning("Duplicate student_id: %s", student_id)
        return False
    except sqlite3.Error as e:
        logger.error("add_student: %s", e)
        return False


def get_all_students():
    sql = """SELECT id, student_id, name, department, face_image, registered_at
             FROM students ORDER BY name"""
    try:
        with _conn() as c:
            return c.execute(sql).fetchall()
    except sqlite3.Error as e:
        logger.error("get_all_students: %s", e)
        return []


def get_student_encodings() -> list:
    sql = "SELECT student_id, name, encoding FROM students"
    try:
        with _conn() as c:
            rows = c.execute(sql).fetchall()
        return [{"student_id": r["student_id"],
                 "name":       r["name"],
                 "encoding":   r["encoding"]} for r in rows]
    except sqlite3.Error as e:
        logger.error("get_student_encodings: %s", e)
        return []


def delete_student(student_id: str) -> bool:
    try:
        with _conn() as c:
            c.execute("DELETE FROM attendance WHERE student_id=?", (student_id,))
            c.execute("DELETE FROM students   WHERE student_id=?", (student_id,))
        logger.info("Deleted: %s", student_id)
        return True
    except sqlite3.Error as e:
        logger.error("delete_student: %s", e)
        return False


def student_exists(student_id: str) -> bool:
    try:
        with _conn() as c:
            return c.execute(
                "SELECT 1 FROM students WHERE student_id=? LIMIT 1",
                (student_id,)
            ).fetchone() is not None
    except sqlite3.Error:
        return False


# ── attendance ─────────────────────────────────────────────────────────────────
def mark_attendance(student_id: str) -> bool:
    today = date.today().isoformat()
    now   = datetime.now().strftime("%H:%M:%S")
    sql   = """INSERT OR IGNORE INTO attendance
               (student_id, date, time, status) VALUES (?,?,?,'Present')"""
    try:
        with _conn() as c:
            cur = c.execute(sql, (student_id, today, now))
            return cur.rowcount > 0
    except sqlite3.Error as e:
        logger.error("mark_attendance: %s", e)
        return False


def get_attendance_by_date(target_date: str):
    sql = """
        SELECT s.student_id, s.name, s.department,
               COALESCE(a.time,'—') AS time,
               CASE WHEN a.status IS NULL THEN 'Absent' ELSE 'Present' END AS status
        FROM students s
        LEFT JOIN attendance a
               ON s.student_id = a.student_id AND a.date = ?
        ORDER BY s.name
    """
    try:
        with _conn() as c:
            return c.execute(sql, (target_date,)).fetchall()
    except sqlite3.Error as e:
        logger.error("get_attendance_by_date: %s", e)
        return []


def get_stats() -> dict:
    today = date.today().isoformat()
    try:
        with _conn() as c:
            total   = c.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            present = c.execute(
                "SELECT COUNT(*) FROM attendance WHERE date=? AND status='Present'",
                (today,)
            ).fetchone()[0]
        return {"total": total, "present": present, "absent": total - present}
    except sqlite3.Error as e:
        logger.error("get_stats: %s", e)
        return {"total": 0, "present": 0, "absent": 0}


def get_all_dates() -> list:
    try:
        with _conn() as c:
            rows = c.execute(
                "SELECT DISTINCT date FROM attendance ORDER BY date DESC"
            ).fetchall()
        return [r[0] for r in rows]
    except sqlite3.Error:
        return []
