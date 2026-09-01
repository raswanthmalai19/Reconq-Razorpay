"""Append-only audit log backed by SQLite -- no update/delete route exists anywhere."""
import json
import os
import time

from sqlalchemy import create_engine, text

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reconq.db")


def get_engine():
    return create_engine(f"sqlite:///{DB_PATH}")


def init_db():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                record_id TEXT,
                timestamp REAL,
                actor TEXT,
                event_type TEXT,
                payload_json TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                record_id TEXT,
                actor TEXT,
                decision TEXT,
                note TEXT,
                timestamp REAL
            )
        """))
    return engine


def append_event(run_id: str, record_id: str, actor: str, event_type: str, payload: dict):
    engine = init_db()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO audit_log (run_id, record_id, timestamp, actor, event_type, payload_json) "
                 "VALUES (:run_id, :record_id, :ts, :actor, :event_type, :payload)"),
            {"run_id": run_id, "record_id": record_id, "ts": time.time(),
             "actor": actor, "event_type": event_type, "payload": json.dumps(payload, default=str)},
        )


def append_override(run_id: str, record_id: str, actor: str, decision: str, note: str):
    engine = init_db()
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO overrides (run_id, record_id, actor, decision, note, timestamp) "
                 "VALUES (:run_id, :record_id, :actor, :decision, :note, :ts)"),
            {"run_id": run_id, "record_id": record_id, "actor": actor,
             "decision": decision, "note": note, "ts": time.time()},
        )


def get_all_events(run_id: str = None):
    engine = init_db()
    with engine.begin() as conn:
        if run_id:
            rows = conn.execute(
                text("SELECT * FROM audit_log WHERE run_id = :run_id ORDER BY id DESC"),
                {"run_id": run_id},
            ).mappings().all()
        else:
            rows = conn.execute(text("SELECT * FROM audit_log ORDER BY id DESC")).mappings().all()
    return [dict(r) for r in rows]
