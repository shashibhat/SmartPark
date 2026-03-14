from __future__ import annotations

import os
from typing import Any

import requests


API_BASE_URL = os.getenv("SMARTPARK_API_URL", "http://127.0.0.1:8000")


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=5)
    response.raise_for_status()
    return response.json()


def _post(path: str, payload: Any) -> Any:
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def _patch(path: str, payload: Any) -> Any:
    response = requests.patch(f"{API_BASE_URL}{path}", json=payload, timeout=5)
    response.raise_for_status()
    return response.json()


def load_lots() -> list[dict[str, Any]]:
    return _get("/lots")["lots"]


def add_lot(payload: dict[str, Any]) -> dict[str, Any]:
    return _post("/lots", payload)["lot"]


def update_spot_status(lot_id: str, spot_label: str, status: str) -> dict[str, Any]:
    return _patch(f"/lots/{lot_id}/spots/{spot_label}", {"status": status})["spot"]


def load_alerts(lot_id: str | None = None) -> list[dict[str, Any]]:
    params = {"lot_id": lot_id} if lot_id else None
    return _get("/alerts", params=params)["alerts"]


def create_alert(payload: dict[str, Any]) -> dict[str, Any]:
    return _post("/alerts", payload)


def load_cameras() -> list[dict[str, Any]]:
    return _get("/cameras")["cameras"]


def add_camera(payload: dict[str, Any]) -> dict[str, Any]:
    return _post("/cameras", payload)["camera"]


def load_analytics(lot_id: str) -> dict[str, Any]:
    return _get(f"/lots/{lot_id}/analytics")


def healthcheck() -> bool:
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        response.raise_for_status()
    except requests.RequestException:
        return False
    return True


def ingest_slot_updates(payload: list[dict[str, Any]]) -> dict[str, Any]:
    return _post("/ingest/slots", payload)
