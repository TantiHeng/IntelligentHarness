import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from src.config import Config
from src.schemas.marketing import MarketingWorkflowState


class SendRecordRepository:
    """
    营销发送记录仓储层。

    当前实现：SQLite。
    默认数据库路径来自 Config.DB_PATH。
    """

    def __init__(self, db_path: str | Path | None = None, config: Config | None = None) -> None:
        self.config = config or Config()
        self.db_path = Path(db_path or self.config.DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_table()
        self._ensure_columns()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS marketing_send_records (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            thread_id TEXT,
            customer_name TEXT NOT NULL,
            customer_contact TEXT,
            product_name TEXT NOT NULL,
            channel TEXT NOT NULL,
            title TEXT,
            body TEXT,
            call_to_action TEXT,
            review_approved INTEGER,
            review_score INTEGER,
            review_reasons TEXT,
            send_success INTEGER,
            provider_message_id TEXT,
            error TEXT,
            raw_state TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """

        with self._connect() as conn:
            conn.execute(sql)
            conn.commit()

    def _ensure_columns(self) -> None:
        """
        兼容旧版本 SQLite 表。

        如果本地已经存在旧表，CREATE TABLE IF NOT EXISTS 不会自动新增字段。
        这里显式补齐 run_id / thread_id，避免旧数据库导致插入失败。
        """
        with self._connect() as conn:
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(marketing_send_records)").fetchall()
            }

            if "run_id" not in columns:
                conn.execute("ALTER TABLE marketing_send_records ADD COLUMN run_id TEXT")

            if "thread_id" not in columns:
                conn.execute("ALTER TABLE marketing_send_records ADD COLUMN thread_id TEXT")

            conn.commit()

    def save(self, state: MarketingWorkflowState) -> str:
        record_id = str(uuid4())

        content = state.content
        review = state.review
        send_result = state.send_result

        sql = """
        INSERT INTO marketing_send_records (
            id,
            run_id,
            thread_id,
            customer_name,
            customer_contact,
            product_name,
            channel,
            title,
            body,
            call_to_action,
            review_approved,
            review_score,
            review_reasons,
            send_success,
            provider_message_id,
            error,
            raw_state,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        values = (
            record_id,
            state.run_id,
            state.thread_id,
            state.input.customer.name,
            state.input.customer.contact,
            state.input.product.name,
            state.input.channel.value,
            content.title if content else None,
            content.body if content else None,
            content.call_to_action if content else None,
            int(review.approved) if review else None,
            review.score if review else None,
            json.dumps(review.reasons, ensure_ascii=False) if review else None,
            int(send_result.success) if send_result else None,
            send_result.provider_message_id if send_result else None,
            self._build_error_text(state),
            state.model_dump_json(ensure_ascii=False),
            datetime.utcnow().isoformat(),
        )

        with self._connect() as conn:
            conn.execute(sql, values)
            conn.commit()

        return record_id

    def get_by_id(self, record_id: str) -> Optional[dict[str, Any]]:
        sql = """
        SELECT *
        FROM marketing_send_records
        WHERE id = ?;
        """

        with self._connect() as conn:
            row = conn.execute(sql, (record_id,)).fetchone()

        return dict(row) if row else None

    def get_by_run_id(self, run_id: str) -> list[dict[str, Any]]:
        sql = """
        SELECT *
        FROM marketing_send_records
        WHERE run_id = ?
        ORDER BY created_at ASC;
        """

        with self._connect() as conn:
            rows = conn.execute(sql, (run_id,)).fetchall()

        return [dict(row) for row in rows]

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        sql = """
        SELECT *
        FROM marketing_send_records
        ORDER BY created_at DESC
        LIMIT ?;
        """

        with self._connect() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()

        return [dict(row) for row in rows]

    @staticmethod
    def _build_error_text(state: MarketingWorkflowState) -> Optional[str]:
        errors = list(state.errors)

        if state.send_result and state.send_result.error:
            errors.append(state.send_result.error)

        if not errors:
            return None

        return "\n".join(errors)
