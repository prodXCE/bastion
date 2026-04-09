import sqlite3
import logging
import hashlib
import secrets
from datetime import datetime

DATABASE_FILE = "bastion.db"


def get_connection():
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_id      TEXT PRIMARY KEY,
            team_name    TEXT NOT NULL,
            api_key_hash TEXT NOT NULL,
            created_at   TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id     TEXT PRIMARY KEY,
            team_id    TEXT NOT NULL,
            repo_url   TEXT NOT NULL,
            cmd        TEXT NOT NULL,
            status     TEXT NOT NULL,
            priority   INTEGER NOT NULL DEFAULT 3,
            cancelled  INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            job_id TEXT PRIMARY KEY,
            output TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id     TEXT,
            level      TEXT NOT NULL,
            message    TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            job_id           TEXT PRIMARY KEY,
            duration_seconds REAL,
            exit_code        INTEGER,
            log_size_bytes   INTEGER,
            recorded_at      TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    logging.info("Database initialized. All tables are ready.")


def log_event(job_id, level, message):
    conn   = get_connection()
    cursor = conn.cursor()
    now    = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO events (job_id, level, message, created_at)
        VALUES (?, ?, ?, ?)
    """, (job_id, level, message, now))
    conn.commit()
    conn.close()


def get_events(job_id=None):
    conn   = get_connection()
    cursor = conn.cursor()
    if job_id:
        cursor.execute("""
            SELECT * FROM events WHERE job_id = ?
            ORDER BY created_at ASC
        """, (job_id,))
    else:
        cursor.execute("SELECT * FROM events ORDER BY created_at ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_job(job_id, team_id, repo_url, cmd, priority=3):
    conn   = get_connection()
    cursor = conn.cursor()
    now    = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO jobs (job_id, team_id, repo_url, cmd, status, priority, cancelled, created_at)
        VALUES (?, ?, ?, ?, 'QUEUED', ?, 0, ?)
    """, (job_id, team_id, repo_url, cmd, priority, now))
    conn.commit()
    conn.close()
    log_event(job_id, "INFO", f"Job {job_id} submitted by team {team_id} with priority {priority}.")


def job_exists(job_id):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT job_id FROM jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_job(job_id):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_next_queued_job():
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM jobs
        WHERE status = 'QUEUED' AND cancelled = 0
        ORDER BY priority ASC, created_at ASC
        LIMIT 1
    """)

    job = cursor.fetchone()
    if job is None:
        conn.close()
        return None

    cursor.execute("""
        UPDATE jobs SET status = 'RUNNING' WHERE job_id = ?
    """, (job["job_id"],))
    conn.commit()
    conn.close()
    return dict(job)


def update_job_status(job_id, status):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE jobs SET status = ? WHERE job_id = ?
    """, (status, job_id))
    conn.commit()
    conn.close()
    log_event(job_id, "INFO", f"Job {job_id} status changed to {status}.")


def cancel_job(job_id):
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        return False

    if row["status"] in ("SUCCESS", "FAILED", "CANCELLED"):
        conn.close()
        return False

    if row["status"] == "QUEUED":
        cursor.execute("""
            UPDATE jobs SET cancelled = 1, status = 'CANCELLED' WHERE job_id = ?
        """, (job_id,))
    else:
        cursor.execute("""
            UPDATE jobs SET cancelled = 1 WHERE job_id = ?
        """, (job_id,))

    conn.commit()
    conn.close()
    log_event(job_id, "INFO", f"Job {job_id} has been cancelled.")
    return True


def is_job_cancelled(job_id):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT cancelled FROM jobs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return False
    return row["cancelled"] == 1


def get_all_jobs():
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_jobs_for_team(team_id):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM jobs WHERE team_id = ?
        ORDER BY created_at DESC
    """, (team_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_log(job_id, output):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO logs (job_id, output)
        VALUES (?, ?)
    """, (job_id, output))
    conn.commit()
    conn.close()


def get_log(job_id):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT output FROM logs WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["output"]
    return "No logs yet. The job may still be running."


def save_metrics(job_id, duration_seconds, exit_code, log_size_bytes):
    conn   = get_connection()
    cursor = conn.cursor()
    now    = datetime.utcnow().isoformat()

    cursor.execute("""
        INSERT OR REPLACE INTO metrics
            (job_id, duration_seconds, exit_code, log_size_bytes, recorded_at)
        VALUES (?, ?, ?, ?, ?)
    """, (job_id, duration_seconds, exit_code, log_size_bytes, now))

    conn.commit()
    conn.close()


def get_metrics(job_id):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM metrics WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_metrics_summary():
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM jobs")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'SUCCESS'")
    success_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'FAILED'")
    failed_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'RUNNING'")
    running_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'QUEUED'")
    queued_count = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(duration_seconds) FROM metrics")
    avg_row = cursor.fetchone()[0]
    avg_duration = round(avg_row, 2) if avg_row else 0

    conn.close()

    success_rate = round((success_count / total * 100), 1) if total > 0 else 0

    return {
        "total_jobs":    total,
        "success_count": success_count,
        "failed_count":  failed_count,
        "running_count": running_count,
        "queued_count":  queued_count,
        "success_rate":  success_rate,
        "avg_duration":  avg_duration
    }


def get_all_metrics():
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.*, j.status, j.team_id
        FROM metrics m
        JOIN jobs j ON m.job_id = j.job_id
        ORDER BY m.recorded_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def generate_api_key():
    random_part = secrets.token_hex(32)
    return f"bstn_{random_part}"


def hash_api_key(raw_key):
    return hashlib.sha256(raw_key.encode()).hexdigest()


def create_team(team_name):
    conn       = get_connection()
    cursor     = conn.cursor()
    team_id    = f"team-{secrets.token_hex(4)}"
    raw_key    = generate_api_key()
    hashed_key = hash_api_key(raw_key)
    now        = datetime.utcnow().isoformat()

    cursor.execute("""
        INSERT INTO teams (team_id, team_name, api_key_hash, created_at)
        VALUES (?, ?, ?, ?)
    """, (team_id, team_name, hashed_key, now))

    conn.commit()
    conn.close()
    log_event(None, "INFO", f"New team registered: {team_name} (ID: {team_id})")

    return {
        "team_id":    team_id,
        "team_name":  team_name,
        "api_key":    raw_key,
        "created_at": now
    }


def get_team_by_api_key(raw_key):
    conn       = get_connection()
    cursor     = conn.cursor()
    hashed_key = hash_api_key(raw_key)
    cursor.execute("SELECT * FROM teams WHERE api_key_hash = ?", (hashed_key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_team(team_id):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teams WHERE team_id = ?", (team_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_all_teams():
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT team_id, team_name, created_at FROM teams
        ORDER BY created_at ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]