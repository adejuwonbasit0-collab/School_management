"""
Database backups.

SQLite (the default for this project) gets a perfect backup: the .db file
is just copied, byte for byte — restoring it is just putting the file back.

For any other database engine (Postgres/MySQL, if DATABASE_URL is set to
one), there's no universal file to copy, so this falls back to a logical
backup: every table's rows dumped to JSON via SQLAlchemy's own metadata,
which is engine-agnostic but not a byte-perfect restore — good enough to
recover data, not a replacement for your host's own DB snapshot feature if
it has one (PythonAnywhere's paid MySQL comes with its own backups too).
"""
import os
import json
import shutil
from datetime import datetime, timedelta

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "instance", "backups")


def _is_sqlite(app):
    return app.config.get("SQLALCHEMY_DATABASE_URI", "").startswith("sqlite:///")


def _sqlite_path(app):
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    path = uri.replace("sqlite:///", "", 1)
    if not os.path.isabs(path):
        # Relative sqlite paths resolve against the app's instance folder
        path = os.path.join(app.instance_path, os.path.basename(path))
    return path


def run_backup(app, db):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    if _is_sqlite(app):
        src = _sqlite_path(app)
        if not os.path.exists(src):
            raise FileNotFoundError(f"SQLite database file not found at {src}")
        filename = f"backup_{ts}.db"
        dest = os.path.join(BACKUP_DIR, filename)
        shutil.copy2(src, dest)
        return filename

    # Non-SQLite fallback: dump every table as JSON
    from sqlalchemy import MetaData, Table, select
    filename = f"backup_{ts}.json"
    dest = os.path.join(BACKUP_DIR, filename)
    metadata = MetaData()
    metadata.reflect(bind=db.engine)
    dump = {}
    with db.engine.connect() as conn:
        for table_name, table in metadata.tables.items():
            rows = conn.execute(select(table)).fetchall()
            dump[table_name] = [dict(row._mapping) for row in rows]
    with open(dest, "w") as f:
        json.dump(dump, f, default=str, indent=2)
    return filename


def list_backups():
    if not os.path.isdir(BACKUP_DIR):
        return []
    files = []
    for name in os.listdir(BACKUP_DIR):
        path = os.path.join(BACKUP_DIR, name)
        if os.path.isfile(path):
            stat = os.stat(path)
            files.append({
                "name": name,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(stat.st_mtime),
            })
    return sorted(files, key=lambda f: f["created_at"], reverse=True)


def prune_old_backups(keep=20):
    """Keep only the most recent N backups so this doesn't quietly fill up
    disk on a host with limited storage (PythonAnywhere free tier especially)."""
    backups = list_backups()
    for old in backups[keep:]:
        try:
            os.remove(os.path.join(BACKUP_DIR, old["name"]))
        except OSError:
            pass


def is_backup_due(frequency_days, last_backup_at):
    """frequency_days: int, e.g. 1 for daily, 7 for weekly, or any custom N.
    last_backup_at: datetime or None."""
    if not last_backup_at:
        return True
    return datetime.utcnow() >= last_backup_at + timedelta(days=frequency_days)


def is_backup_due_on_day_of_month(day_of_month, last_backup_at, now=None):
    """Alternative schedule mode: run on a fixed calendar day every month
    (e.g. the 1st) instead of "every N days since last backup". Due when
    today's day-of-month matches (clamped to the month's actual last day,
    so day_of_month=31 still fires in February) and no backup has run yet
    today — since the external cron only fires once a day, this simply
    guards against double-firing if it's ever triggered twice in one day."""
    now = now or datetime.utcnow()
    import calendar
    last_day_this_month = calendar.monthrange(now.year, now.month)[1]
    target_day = min(int(day_of_month or 1), last_day_this_month)
    if now.day != target_day:
        return False
    if last_backup_at and last_backup_at.date() == now.date():
        return False
    return True
