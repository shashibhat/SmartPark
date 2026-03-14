from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from smartpark.demo_data import (
    default_alerts,
    default_cameras,
    default_lots,
    default_status_history,
    timestamp_now,
)


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_FILE = DATA_DIR / "smartpark.db"


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    connection = _connect()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    if column_name not in _column_names(connection, table_name):
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS lots (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                kind TEXT NOT NULL CHECK(kind IN ('indoor', 'outdoor')),
                description TEXT NOT NULL,
                camera_count INTEGER NOT NULL,
                map_lat REAL NOT NULL,
                map_lng REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS spots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_id TEXT NOT NULL,
                label TEXT NOT NULL,
                zone TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('free', 'occupied')),
                lat REAL,
                lng REAL,
                led_channel TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (lot_id) REFERENCES lots(id) ON DELETE CASCADE,
                UNIQUE (lot_id, label)
            );

            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_id TEXT NOT NULL,
                name TEXT NOT NULL,
                rtsp_url TEXT NOT NULL,
                status TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                FOREIGN KEY (lot_id) REFERENCES lots(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_id TEXT,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (lot_id) REFERENCES lots(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                spot_label TEXT,
                status TEXT,
                occupied_count INTEGER,
                total_count INTEGER,
                avg_wait_minutes REAL,
                turnover_count INTEGER,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (lot_id) REFERENCES lots(id) ON DELETE CASCADE
            );
            """
        )
        _ensure_column(connection, "spots", "spot_type", "TEXT NOT NULL DEFAULT 'standard'")
        _ensure_column(connection, "spots", "width_class", "TEXT NOT NULL DEFAULT 'standard'")
        _ensure_column(connection, "spots", "distance_rank", "INTEGER NOT NULL DEFAULT 999")
        _ensure_column(connection, "spots", "is_covered", "INTEGER NOT NULL DEFAULT 0")


def seed_demo_data() -> None:
    init_db()
    with get_connection() as connection:
        lot_row = connection.execute("SELECT COUNT(*) AS count FROM lots").fetchone()
        if lot_row["count"] == 0:
            for lot in default_lots():
                _insert_lot(connection, lot)

        camera_row = connection.execute("SELECT COUNT(*) AS count FROM cameras").fetchone()
        if camera_row["count"] == 0:
            for camera in default_cameras():
                connection.execute(
                    """
                    INSERT INTO cameras (lot_id, name, rtsp_url, status, last_seen)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        camera["lot_id"],
                        camera["name"],
                        camera["rtsp_url"],
                        camera["status"],
                        camera["last_seen"],
                    ),
                )

        alert_row = connection.execute("SELECT COUNT(*) AS count FROM alerts").fetchone()
        if alert_row["count"] == 0:
            for alert in default_alerts():
                connection.execute(
                    """
                    INSERT INTO alerts (lot_id, severity, category, message, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        alert["lot_id"],
                        alert["severity"],
                        alert["category"],
                        alert["message"],
                        alert["status"],
                        alert["created_at"],
                    ),
                )

        history_row = connection.execute("SELECT COUNT(*) AS count FROM status_history").fetchone()
        if history_row["count"] == 0:
            for event in default_status_history():
                connection.execute(
                    """
                    INSERT INTO status_history (
                        lot_id, event_type, spot_label, status, occupied_count, total_count,
                        avg_wait_minutes, turnover_count, recorded_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event["lot_id"],
                        event["event_type"],
                        event["spot_label"],
                        event["status"],
                        event["occupied_count"],
                        event["total_count"],
                        event["avg_wait_minutes"],
                        event["turnover_count"],
                        event["recorded_at"],
                    ),
                )


def _insert_lot(connection: sqlite3.Connection, lot: dict[str, Any]) -> None:
    created_at = timestamp_now()
    connection.execute(
        """
        INSERT INTO lots (id, name, kind, description, camera_count, map_lat, map_lng, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            lot["id"],
            lot["name"],
            lot["kind"],
            lot["description"],
            int(lot["camera_count"]),
            float(lot["map_center"]["lat"]),
            float(lot["map_center"]["lng"]),
            created_at,
            created_at,
        ),
    )
    for spot in lot["spots"]:
        connection.execute(
            """
            INSERT INTO spots (
                lot_id, label, zone, status, lat, lng, led_channel, updated_at,
                spot_type, width_class, distance_rank, is_covered
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lot["id"],
                spot["label"],
                spot["zone"],
                spot["status"],
                spot.get("lat"),
                spot.get("lng"),
                spot.get("led_channel"),
                spot.get("updated_at", created_at),
                spot.get("spot_type", "standard"),
                spot.get("width_class", "standard"),
                spot.get("distance_rank", 999),
                int(spot.get("is_covered", 0)),
            ),
        )


def load_lots() -> list[dict[str, Any]]:
    seed_demo_data()
    with get_connection() as connection:
        lot_rows = connection.execute(
            """
            SELECT id, name, kind, description, camera_count, map_lat, map_lng, updated_at
            FROM lots
            ORDER BY name
            """
        ).fetchall()
        spots_by_lot: dict[str, list[dict[str, Any]]] = {}
        for spot_row in connection.execute(
            """
            SELECT lot_id, label, zone, status, lat, lng, led_channel, updated_at,
                   spot_type, width_class, distance_rank, is_covered
            FROM spots
            ORDER BY lot_id, distance_rank, label
            """
        ).fetchall():
            spots_by_lot.setdefault(spot_row["lot_id"], []).append(
                {
                    "label": spot_row["label"],
                    "zone": spot_row["zone"],
                    "status": spot_row["status"],
                    "lat": spot_row["lat"],
                    "lng": spot_row["lng"],
                    "led_channel": spot_row["led_channel"],
                    "updated_at": spot_row["updated_at"],
                    "spot_type": spot_row["spot_type"],
                    "width_class": spot_row["width_class"],
                    "distance_rank": spot_row["distance_rank"],
                    "is_covered": bool(spot_row["is_covered"]),
                }
            )

    lots = []
    for row in lot_rows:
        spots = spots_by_lot.get(row["id"], [])
        lots.append(
            {
                "id": row["id"],
                "name": row["name"],
                "kind": row["kind"],
                "description": row["description"],
                "camera_count": row["camera_count"],
                "map_center": {"lat": row["map_lat"], "lng": row["map_lng"]},
                "updated_at": row["updated_at"],
                "spots": spots,
                "free_count": sum(1 for spot in spots if spot["status"] == "free"),
            }
        )
    return lots


def add_lot(payload: dict[str, Any]) -> dict[str, Any]:
    seed_demo_data()
    timestamp = timestamp_now()
    lot_id = f"{payload['name'].lower().replace(' ', '-')}-{uuid4().hex[:6]}"
    center = payload["map_center"]
    lot = {
        "id": lot_id,
        "name": payload["name"],
        "kind": payload["kind"],
        "description": payload["description"] or "New SmartPark lot",
        "camera_count": int(payload["camera_count"]),
        "map_center": {"lat": float(center["lat"]), "lng": float(center["lng"])},
        "spots": [],
    }
    for index, label in enumerate(payload["spots"], start=1):
        spot_type = payload.get("spot_type", "standard")
        width_class = payload.get("width_class", "standard")
        spot = {
            "label": label,
            "zone": payload.get("zone", "General"),
            "status": "free",
            "updated_at": timestamp,
            "spot_type": spot_type,
            "width_class": width_class,
            "distance_rank": index,
            "is_covered": 0 if payload["kind"] == "outdoor" else 1,
        }
        if payload["kind"] == "outdoor":
            offset = index * 0.00003
            spot["lat"] = round(float(center["lat"]) + offset, 6)
            spot["lng"] = round(float(center["lng"]) + offset, 6)
            spot["led_channel"] = None
        else:
            spot["lat"] = None
            spot["lng"] = None
            spot["led_channel"] = f"GPIO-{index:02d}"
        lot["spots"].append(spot)

    with get_connection() as connection:
        _insert_lot(connection, lot)
        connection.execute(
            """
            INSERT INTO status_history (
                lot_id, event_type, spot_label, status, occupied_count, total_count,
                avg_wait_minutes, turnover_count, recorded_at
            )
            VALUES (?, 'snapshot', NULL, NULL, 0, ?, 0.0, 0, ?)
            """,
            (lot_id, len(lot["spots"]), timestamp),
        )
    return next(saved for saved in load_lots() if saved["id"] == lot_id)


def update_spot_status(lot_id: str, spot_label: str, status: str) -> dict[str, Any]:
    seed_demo_data()
    timestamp = timestamp_now()
    with get_connection() as connection:
        result = connection.execute(
            """
            UPDATE spots
            SET status = ?, updated_at = ?
            WHERE lot_id = ? AND label = ?
            """,
            (status, timestamp, lot_id, spot_label),
        )
        if result.rowcount == 0:
            raise ValueError(f"Unknown spot {spot_label} for lot {lot_id}")
        connection.execute("UPDATE lots SET updated_at = ? WHERE id = ?", (timestamp, lot_id))
        lot_stats = connection.execute(
            "SELECT COUNT(*) AS total_count, SUM(CASE WHEN status = 'occupied' THEN 1 ELSE 0 END) AS occupied_count FROM spots WHERE lot_id = ?",
            (lot_id,),
        ).fetchone()
        connection.execute(
            """
            INSERT INTO status_history (
                lot_id, event_type, spot_label, status, occupied_count, total_count,
                avg_wait_minutes, turnover_count, recorded_at
            )
            VALUES (?, 'spot_update', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lot_id,
                spot_label,
                status,
                lot_stats["occupied_count"] or 0,
                lot_stats["total_count"] or 0,
                round(1 + ((lot_stats["occupied_count"] or 0) / max(lot_stats["total_count"] or 1, 1)) * 2.5, 2),
                1,
                timestamp,
            ),
        )
        occupancy_ratio = (lot_stats["occupied_count"] or 0) / max(lot_stats["total_count"] or 1, 1)
        if occupancy_ratio >= 0.8:
            connection.execute(
                """
                INSERT INTO alerts (lot_id, severity, category, message, status, created_at)
                VALUES (?, 'warning', 'capacity', ?, 'open', ?)
                """,
                (lot_id, f"Lot crossed {int(occupancy_ratio * 100)}% occupancy.", timestamp),
            )
    lots = load_lots()
    for lot in lots:
        if lot["id"] != lot_id:
            continue
        for spot in lot["spots"]:
            if spot["label"] == spot_label:
                return spot
    raise ValueError(f"Unknown spot {spot_label} for lot {lot_id}")


def list_cameras() -> list[dict[str, Any]]:
    seed_demo_data()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, lot_id, name, rtsp_url, status, last_seen
            FROM cameras
            ORDER BY lot_id, name
            """
        ).fetchall()
    return [dict(row) for row in rows]


def add_camera(payload: dict[str, Any]) -> dict[str, Any]:
    seed_demo_data()
    now = timestamp_now()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO cameras (lot_id, name, rtsp_url, status, last_seen)
            VALUES (?, ?, ?, ?, ?)
            """,
            (payload["lot_id"], payload["name"], payload["rtsp_url"], payload.get("status", "online"), now),
        )
        connection.execute(
            "UPDATE lots SET camera_count = camera_count + 1, updated_at = ? WHERE id = ?",
            (now, payload["lot_id"]),
        )
        camera_id = cursor.lastrowid
    return next(camera for camera in list_cameras() if camera["id"] == camera_id)


def list_alerts(lot_id: str | None = None) -> list[dict[str, Any]]:
    seed_demo_data()
    with get_connection() as connection:
        if lot_id:
            rows = connection.execute(
                """
                SELECT id, lot_id, severity, category, message, status, created_at
                FROM alerts
                WHERE lot_id = ?
                ORDER BY datetime(created_at) DESC
                """,
                (lot_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, lot_id, severity, category, message, status, created_at
                FROM alerts
                ORDER BY datetime(created_at) DESC
                """
            ).fetchall()
    return [dict(row) for row in rows]


def create_alert(lot_id: str | None, severity: str, category: str, message: str, status: str = "open") -> None:
    seed_demo_data()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO alerts (lot_id, severity, category, message, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (lot_id, severity, category, message, status, timestamp_now()),
        )


def get_lot_analytics(lot_id: str) -> dict[str, Any]:
    seed_demo_data()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT occupied_count, total_count, avg_wait_minutes, turnover_count, recorded_at
            FROM status_history
            WHERE lot_id = ? AND event_type = 'snapshot'
            ORDER BY datetime(recorded_at) ASC
            LIMIT 24
            """,
            (lot_id,),
        ).fetchall()
        latest = connection.execute(
            """
            SELECT occupied_count, total_count, avg_wait_minutes, turnover_count, recorded_at
            FROM status_history
            WHERE lot_id = ?
            ORDER BY datetime(recorded_at) DESC
            LIMIT 1
            """,
            (lot_id,),
        ).fetchone()

    hourly = []
    for row in rows:
        total = row["total_count"] or 1
        occupancy_pct = round(((row["occupied_count"] or 0) / total) * 100, 1)
        hourly.append(
            {
                "timestamp": row["recorded_at"],
                "occupancy_pct": occupancy_pct,
                "avg_wait_minutes": row["avg_wait_minutes"] or 0.0,
                "turnover_count": row["turnover_count"] or 0,
            }
        )

    peak = max(hourly, key=lambda item: item["occupancy_pct"], default=None)
    return {
        "hourly": hourly,
        "summary": {
            "peak_occupancy_pct": peak["occupancy_pct"] if peak else 0,
            "peak_hour": peak["timestamp"] if peak else None,
            "avg_wait_minutes": latest["avg_wait_minutes"] if latest else 0.0,
            "turnover_today": sum(item["turnover_count"] for item in hourly[-8:]),
        },
    }
