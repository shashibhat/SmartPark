from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from smartpark.storage import (
    add_camera,
    add_lot,
    create_alert,
    get_lot_analytics,
    list_alerts,
    list_cameras,
    load_lots,
    seed_demo_data,
    update_spot_status,
)


class MapCenter(BaseModel):
    lat: float
    lng: float


class LotCreate(BaseModel):
    name: str
    kind: Literal["indoor", "outdoor"]
    description: str = ""
    camera_count: int = Field(ge=1, le=100)
    map_center: MapCenter
    spots: list[str] = Field(min_length=1)
    zone: str = "General"
    spot_type: Literal["standard", "ev", "accessible"] = "standard"
    width_class: Literal["compact", "standard", "wide"] = "standard"


class SpotStatusUpdate(BaseModel):
    status: Literal["free", "occupied"]


class WorkerSpotUpdate(BaseModel):
    lot_id: str
    label: str
    status: Literal["free", "occupied"]


class CameraCreate(BaseModel):
    lot_id: str
    name: str
    rtsp_url: str
    status: Literal["online", "warning", "offline"] = "online"


class AlertCreate(BaseModel):
    lot_id: str | None = None
    severity: Literal["info", "warning", "critical"]
    category: str
    message: str
    status: Literal["open", "resolved"] = "open"


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        disconnected: list[WebSocket] = []
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except RuntimeError:
                disconnected.append(websocket)
        for websocket in disconnected:
            self.disconnect(websocket)


manager = ConnectionManager()
app = FastAPI(title="SmartPark Local API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def broadcast_snapshot(event: str) -> None:
    await manager.broadcast(
        {
            "event": event,
            "lots": load_lots(),
            "alerts": list_alerts(),
            "cameras": list_cameras(),
        }
    )


@app.on_event("startup")
async def startup_event() -> None:
    seed_demo_data()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/lots")
def lots() -> dict:
    items = load_lots()
    return {"lots": items, "count": len(items)}


@app.post("/lots", status_code=201)
async def create_lot(payload: LotCreate) -> dict:
    lot = add_lot(payload.model_dump())
    await broadcast_snapshot("lot_created")
    return {"lot": lot}


@app.patch("/lots/{lot_id}/spots/{spot_label}")
async def patch_spot_status(lot_id: str, spot_label: str, payload: SpotStatusUpdate) -> dict:
    try:
        spot = update_spot_status(lot_id, spot_label, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await broadcast_snapshot("spot_updated")
    return {"spot": spot}


@app.get("/lots/{lot_id}/analytics")
def lot_analytics(lot_id: str) -> dict:
    return get_lot_analytics(lot_id)


@app.post("/ingest/slots")
async def ingest_slot_updates(payload: list[WorkerSpotUpdate]) -> dict:
    updated = 0
    for item in payload:
        try:
            update_spot_status(item.lot_id, item.label, item.status)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        updated += 1
    await broadcast_snapshot("worker_ingest")
    return {"updated": updated}


@app.get("/alerts")
def alerts(lot_id: str | None = Query(default=None)) -> dict:
    items = list_alerts(lot_id)
    return {"alerts": items, "count": len(items)}


@app.post("/alerts", status_code=201)
async def add_alert(payload: AlertCreate) -> dict:
    create_alert(payload.lot_id, payload.severity, payload.category, payload.message, payload.status)
    await broadcast_snapshot("alert_created")
    return {"ok": True}


@app.get("/cameras")
def cameras() -> dict:
    items = list_cameras()
    return {"cameras": items, "count": len(items)}


@app.post("/cameras", status_code=201)
async def create_camera(payload: CameraCreate) -> dict:
    camera = add_camera(payload.model_dump())
    await broadcast_snapshot("camera_created")
    return {"camera": camera}


@app.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    await websocket.send_json(
        {
            "event": "snapshot",
            "lots": load_lots(),
            "alerts": list_alerts(),
            "cameras": list_cameras(),
        }
    )
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except RuntimeError:
        manager.disconnect(websocket)
