"""SQLite 审计适配器：持久化运行记录和业务事件，不决定告警策略。"""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from intelligent_harness.events import BusinessEvent
from intelligent_harness.models import HarnessWorkflowState


class SQLiteAuditRepository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_tables(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS harness_audit_records (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL, thread_id TEXT NOT NULL,
                    scenario TEXT NOT NULL, input_json TEXT NOT NULL, output_json TEXT,
                    review_json TEXT, error TEXT, raw_state TEXT NOT NULL, created_at TEXT NOT NULL
                );"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS harness_business_events (
                    event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, thread_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL, severity INTEGER NOT NULL, event_type TEXT NOT NULL,
                    step TEXT NOT NULL, scenario TEXT NOT NULL, inference_attempt INTEGER NOT NULL,
                    review_attempt INTEGER, content_json TEXT, reasons_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );"""
            )

    def save_run(self, state: HarnessWorkflowState) -> str:
        record_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO harness_audit_records (
                    id, run_id, thread_id, scenario, input_json, output_json, review_json,
                    error, raw_state, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                (
                    record_id,
                    state.run_id,
                    state.thread_id,
                    state.scenario,
                    self._json(state.input),
                    self._json(state.output),
                    self._json(state.review),
                    "\n".join(state.errors) or None,
                    state.model_dump_json(ensure_ascii=False),
                    datetime.now(UTC).isoformat(),
                ),
            )
        return record_id

    def save_event(self, event: BusinessEvent) -> str:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO harness_business_events (
                    event_id, run_id, thread_id, timestamp, severity, event_type, step, scenario,
                    inference_attempt, review_attempt, content_json, reasons_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
                (
                    event.event_id,
                    event.run_id,
                    event.thread_id,
                    event.timestamp.isoformat(),
                    event.severity,
                    event.event_type.value,
                    event.step,
                    event.scenario,
                    event.inference_attempt,
                    event.review_attempt,
                    self._json(event.content),
                    self._json(event.reasons),
                    self._json(event.metadata),
                ),
            )
        return event.event_id

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM harness_business_events WHERE run_id = ? ORDER BY timestamp ASC;",
                (run_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _json(value: Any) -> str | None:
        if value is None:
            return None
        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="json")
        return json.dumps(value, ensure_ascii=False)
