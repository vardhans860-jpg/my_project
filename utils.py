"""
utils.py  —  Input validation, CSV export, logging setup.
"""

import re
import csv
import logging
import logging.handlers
from pathlib import Path
from datetime import date

BASE_DIR    = Path(__file__).resolve().parent
LOG_DIR     = BASE_DIR / "logs"
EXPORT_DIR  = BASE_DIR / "exports"
LOG_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

# ── logging ────────────────────────────────────────────────────────────────────
def setup_logging():
    log_file = LOG_DIR / "app.log"
    handler  = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s"
    ))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    # Console handler (no sensitive data)
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    root.addHandler(ch)


# ── input validation ───────────────────────────────────────────────────────────
_ID_RE   = re.compile(r'^[A-Za-z0-9_\-]{1,20}$')
_NAME_RE = re.compile(r"^[A-Za-z\s'\.]{2,50}$")
_DEPT_RE = re.compile(r'^[A-Za-z0-9\s&\-]{1,50}$')


def validate_student_id(sid: str) -> tuple[bool, str]:
    sid = sid.strip()
    if not sid:
        return False, "Student ID cannot be empty."
    if not _ID_RE.match(sid):
        return False, "ID must be 1–20 alphanumeric / _ - characters."
    return True, ""


def validate_name(name: str) -> tuple[bool, str]:
    name = name.strip()
    if not name:
        return False, "Name cannot be empty."
    if not _NAME_RE.match(name):
        return False, "Name must be 2–50 letters only."
    return True, ""


def validate_department(dept: str) -> tuple[bool, str]:
    dept = dept.strip()
    if not dept:
        return True, ""           # optional field
    if not _DEPT_RE.match(dept):
        return False, "Department contains invalid characters."
    return True, ""


# ── CSV export ─────────────────────────────────────────────────────────────────
def export_attendance_csv(rows, target_date: str | None = None) -> Path:
    """
    Export attendance rows to a timestamped CSV file in exports/.
    `rows` must be sqlite3.Row objects with keys:
        student_id, name, department, time, status
    """
    if target_date is None:
        target_date = date.today().isoformat()
    filename = EXPORT_DIR / f"attendance_{target_date}.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Student ID", "Name", "Department", "Time", "Status", "Date"])
        for row in rows:
            writer.writerow([
                row["student_id"],
                row["name"],
                row["department"],
                row["time"],
                row["status"],
                target_date,
            ])
    return filename
