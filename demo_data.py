from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def timestamp_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def default_lots() -> list[dict[str, Any]]:
    timestamp = timestamp_now()
    return [
        {
            "id": "westfield-top-deck",
            "name": "The Grove Mall Lot A",
            "kind": "outdoor",
            "description": "Open-air mall lot with pole-mounted cameras and navigation-first driver flow.",
            "camera_count": 6,
            "map_center": {"lat": 34.072240, "lng": -118.359245},
            "spots": [
                {
                    "label": "A-12",
                    "zone": "North Row",
                    "status": "free",
                    "lat": 34.072291,
                    "lng": -118.359391,
                    "spot_type": "standard",
                    "width_class": "wide",
                    "distance_rank": 1,
                    "is_covered": 0,
                    "updated_at": timestamp,
                },
                {
                    "label": "A-13",
                    "zone": "North Row",
                    "status": "occupied",
                    "lat": 34.072254,
                    "lng": -118.359341,
                    "spot_type": "ev",
                    "width_class": "standard",
                    "distance_rank": 2,
                    "is_covered": 0,
                    "updated_at": timestamp,
                },
                {
                    "label": "B-04",
                    "zone": "Center Lane",
                    "status": "free",
                    "lat": 34.072190,
                    "lng": -118.359201,
                    "spot_type": "accessible",
                    "width_class": "wide",
                    "distance_rank": 3,
                    "is_covered": 0,
                    "updated_at": timestamp,
                },
                {
                    "label": "C-18",
                    "zone": "South Row",
                    "status": "occupied",
                    "lat": 34.072133,
                    "lng": -118.359077,
                    "spot_type": "standard",
                    "width_class": "compact",
                    "distance_rank": 4,
                    "is_covered": 0,
                    "updated_at": timestamp,
                },
            ],
        },
        {
            "id": "dtla-garage-l2",
            "name": "DTLA Garage L2",
            "kind": "indoor",
            "description": "Indoor LED-driven garage floor with overhead coverage and bay-level guidance.",
            "camera_count": 3,
            "map_center": {"lat": 34.046900, "lng": -118.256800},
            "spots": [
                {
                    "label": "L2-01",
                    "zone": "Blue Zone",
                    "status": "free",
                    "led_channel": "GPIO-01",
                    "spot_type": "standard",
                    "width_class": "standard",
                    "distance_rank": 1,
                    "is_covered": 1,
                    "updated_at": timestamp,
                },
                {
                    "label": "L2-02",
                    "zone": "Blue Zone",
                    "status": "occupied",
                    "led_channel": "GPIO-02",
                    "spot_type": "ev",
                    "width_class": "standard",
                    "distance_rank": 2,
                    "is_covered": 1,
                    "updated_at": timestamp,
                },
                {
                    "label": "L2-03",
                    "zone": "Blue Zone",
                    "status": "free",
                    "led_channel": "GPIO-03",
                    "spot_type": "standard",
                    "width_class": "wide",
                    "distance_rank": 3,
                    "is_covered": 1,
                    "updated_at": timestamp,
                },
                {
                    "label": "L2-04",
                    "zone": "Orange Zone",
                    "status": "occupied",
                    "led_channel": "GPIO-04",
                    "spot_type": "accessible",
                    "width_class": "wide",
                    "distance_rank": 4,
                    "is_covered": 1,
                    "updated_at": timestamp,
                },
                {
                    "label": "L2-05",
                    "zone": "Orange Zone",
                    "status": "free",
                    "led_channel": "GPIO-05",
                    "spot_type": "standard",
                    "width_class": "compact",
                    "distance_rank": 5,
                    "is_covered": 1,
                    "updated_at": timestamp,
                },
            ],
        },
    ]


def default_cameras() -> list[dict[str, Any]]:
    now = timestamp_now()
    return [
        {
            "lot_id": "westfield-top-deck",
            "name": "North Pole Cam 01",
            "rtsp_url": "rtsp://192.168.1.50:554/stream1",
            "status": "online",
            "last_seen": now,
        },
        {
            "lot_id": "westfield-top-deck",
            "name": "Center Pole Cam 02",
            "rtsp_url": "rtsp://192.168.1.51:554/stream1",
            "status": "online",
            "last_seen": now,
        },
        {
            "lot_id": "dtla-garage-l2",
            "name": "Garage Overhead Cam A",
            "rtsp_url": "rtsp://192.168.1.70:554/stream1",
            "status": "warning",
            "last_seen": now,
        },
    ]


def default_alerts() -> list[dict[str, Any]]:
    now = datetime.now()
    return [
        {
            "lot_id": "westfield-top-deck",
            "severity": "warning",
            "category": "capacity",
            "message": "Lot A crossed 75% occupancy during lunch rush.",
            "status": "open",
            "created_at": (now - timedelta(minutes=7)).strftime("%Y-%m-%d %H:%M:%S"),
        },
        {
            "lot_id": "dtla-garage-l2",
            "severity": "critical",
            "category": "camera",
            "message": "Garage Overhead Cam A jitter exceeded threshold for 90 seconds.",
            "status": "open",
            "created_at": (now - timedelta(minutes=18)).strftime("%Y-%m-%d %H:%M:%S"),
        },
        {
            "lot_id": "dtla-garage-l2",
            "severity": "info",
            "category": "accessible",
            "message": "Accessible bay L2-04 was manually verified by staff.",
            "status": "resolved",
            "created_at": (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
        },
    ]


def default_status_history() -> list[dict[str, Any]]:
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    history: list[dict[str, Any]] = []
    for hour_offset in range(24):
        event_time = now - timedelta(hours=23 - hour_offset)
        grove_ratio = [0.82, 0.79, 0.76, 0.71, 0.66, 0.61, 0.57, 0.54, 0.47, 0.39, 0.34, 0.29][hour_offset % 12]
        dtla_ratio = [0.91, 0.88, 0.85, 0.79, 0.74, 0.69, 0.66, 0.62, 0.55, 0.49, 0.45, 0.40][hour_offset % 12]
        history.append(
            {
                "lot_id": "westfield-top-deck",
                "event_type": "snapshot",
                "spot_label": None,
                "status": None,
                "occupied_count": round(4 * grove_ratio),
                "total_count": 4,
                "avg_wait_minutes": round(1.1 + grove_ratio * 1.9, 2),
                "turnover_count": 12 + hour_offset,
                "recorded_at": event_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        history.append(
            {
                "lot_id": "dtla-garage-l2",
                "event_type": "snapshot",
                "spot_label": None,
                "status": None,
                "occupied_count": round(5 * dtla_ratio),
                "total_count": 5,
                "avg_wait_minutes": round(1.4 + dtla_ratio * 2.2, 2),
                "turnover_count": 9 + hour_offset,
                "recorded_at": event_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return history
