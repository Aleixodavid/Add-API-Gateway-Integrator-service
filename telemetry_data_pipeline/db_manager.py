"""DB Manager — Gerenciador SQLite com índices de alta performance."""

import os
import json
import sqlite3
import logging

logger = logging.getLogger("TelemetryDB")


class TelemetryDBManager:
    """Gerenciador de banco de dados SQLite para métricas de telemetria."""

    def __init__(self, db_path: str = "metrics.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-4000")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                event_type TEXT NOT NULL,
                metric_name TEXT,
                metric_value REAL NOT NULL,
                unit TEXT DEFAULT 'count',
                tags_json TEXT DEFAULT '{}',
                event_timestamp REAL NOT NULL,
                ingested_at REAL NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_te_source ON telemetry_events(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_te_type ON telemetry_events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_te_ts ON telemetry_events(event_timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_te_source_type ON telemetry_events(source, event_type)")
        conn.commit()
        conn.close()
        logger.info(f"[TelemetryDB] Banco inicializado em: {self.db_path}")

    def insert_event(self, event: dict):
        conn = self._get_conn()
        conn.execute("""
            INSERT OR IGNORE INTO telemetry_events
            (event_id, source, event_type, metric_name, metric_value, unit, tags_json, event_timestamp, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event["event_id"], event["source"], event["event_type"],
            event.get("metric_name", ""), event["metric_value"],
            event.get("unit", "count"),
            json.dumps(event.get("tags", {}), ensure_ascii=False),
            event["timestamp"], event["ingested_at"],
        ))
        conn.commit()
        conn.close()

    def count_records(self) -> int:
        conn = self._get_conn()
        count = conn.execute("SELECT COUNT(*) FROM telemetry_events").fetchone()[0]
        conn.close()
        return count

    def list_events(self, limit: int = 50, offset: int = 0) -> dict:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM telemetry_events ORDER BY event_timestamp DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        total = self.count_records()
        conn.close()
        return {
            "events": [dict(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_summary_report(self) -> dict:
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as total_events,
                COUNT(DISTINCT source) as unique_sources,
                COUNT(DISTINCT event_type) as unique_types,
                AVG(metric_value) as avg_value,
                MIN(metric_value) as min_value,
                MAX(metric_value) as max_value,
                MIN(event_timestamp) as first_event,
                MAX(event_timestamp) as last_event
            FROM telemetry_events
        """)
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else {}

    def get_report_by_source(self) -> dict:
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT source,
                   COUNT(*) as event_count,
                   AVG(metric_value) as avg_value,
                   MIN(metric_value) as min_value,
                   MAX(metric_value) as max_value
            FROM telemetry_events
            GROUP BY source
            ORDER BY event_count DESC
        """).fetchall()
        conn.close()
        return {"sources": [dict(r) for r in rows]}

    def get_report_by_period(self, granularity: str = "hour") -> dict:
        if granularity == "day":
            fmt = "%Y-%m-%d"
        else:
            fmt = "%Y-%m-%d %H:00"

        conn = self._get_conn()
        rows = conn.execute(f"""
            SELECT strftime('{fmt}', event_timestamp, 'unixepoch') as period,
                   COUNT(*) as event_count,
                   AVG(metric_value) as avg_value
            FROM telemetry_events
            GROUP BY period
            ORDER BY period DESC
            LIMIT 100
        """).fetchall()
        conn.close()
        return {"periods": [dict(r) for r in rows], "granularity": granularity}
