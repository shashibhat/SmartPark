# SmartPark AI Local Stack

Local-first SmartPark with:

- SQLite as the shared state store
- FastAPI for the local HTTP + WebSocket API
- Streamlit for a market-ready operator dashboard and admin tools
- seeded demo lots so the whole stack runs before YOLO is connected

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn smartpark.api:app --reload
```

In a second terminal:

```bash
source .venv/bin/activate
streamlit run app.py
```

The API seeds and stores state in [`data/smartpark.db`](/Users/bytedance/personal/SmartPark/data/smartpark.db). The older [`data/lots.json`](/Users/bytedance/personal/SmartPark/data/lots.json) file is now just sample seed/reference data.

## Product UI

- `Dashboard`: top live bar, big lot view, routing filters, shareable spot link, CSV export
- `Admin`: add a lot fast and simulate occupancy changes
- `Analytics`: occupancy trend, wait estimate, turnover, peak-hour view
- `Settings`: camera stream manager and LED test controls
- `Alerts Log`: severity-filtered operational events

## Included on purpose

- Multi-lot support in one dashboard
- Outdoor map mode plus indoor LED-mirroring grid mode
- Spot filters for EV, accessible, wide, and covered bays
- Local alert log for capacity, camera health, and ops actions
- Camera inventory and live RTSP metadata
- Exportable CSV snapshots and analytics

## Deferred on purpose

- Reservations / “hold this spot”
- Predictive availability promises
- Weather-aware behavior

These are useful, but they need more policy, historical confidence, and abuse prevention than a first real local release should pretend to have.

## API surface

- `GET /health`: simple liveness check
- `GET /lots`: current nested lot + spot snapshot
- `GET /lots/{lot_id}/analytics`: occupancy history and summary metrics
- `GET /alerts`: alert feed
- `GET /cameras`: camera inventory
- `POST /lots`: create a new lot
- `PATCH /lots/{lot_id}/spots/{spot_label}`: flip one spot state
- `POST /ingest/slots`: batch worker updates from YOLO/ParkingManagement
- `POST /alerts`: append a local ops alert
- `POST /cameras`: register a camera stream
- `WS /ws/updates`: push live snapshots to local clients

## Next integration step

Point the YOLO + Ultralytics ParkingManagement worker at [`/ingest/slots`](http://127.0.0.1:8000/ingest/slots) so each detection cycle posts a batch like:

```json
[
  {"lot_id": "westfield-top-deck", "label": "A-12", "status": "occupied"},
  {"lot_id": "westfield-top-deck", "label": "B-04", "status": "free"}
]
```

That keeps the dashboard, indoor LED controller, and any future mobile app all reading from the same local API contract.

## Worker adapter

The worker-side adapter lives in [smartpark/worker.py](/Users/bytedance/personal/SmartPark/smartpark/worker.py). It accepts a few input shapes and normalizes them into the batch API payload:

- simple mapping: `{"A-12": "occupied", "B-04": "free"}`
- list of regions: `[{"label": "A-12", "occupied": true}]`
- wrapper object: `{"slots": [...]}`

It also remembers the last sent state and only posts spot changes, which is useful when your detector loop is running every 2-5 seconds.

Run a sample snapshot:

```bash
python -m smartpark.worker from-file \
  --lot-id westfield-top-deck \
  --input data/parking_snapshot.sample.json \
  --once
```

Run a deterministic demo loop:

```bash
python -m smartpark.worker demo \
  --lot-id westfield-top-deck \
  --cycles 10 \
  --poll-seconds 2
```

## ParkingManagement hook

When you wire in the real Ultralytics loop, the seam is:

```python
from smartpark.worker import SmartParkIngestAdapter

adapter = SmartParkIngestAdapter(lot_id="westfield-top-deck")

# Replace `parking_regions_snapshot` with whatever your detector returns each cycle.
parking_regions_snapshot = [
    {"label": "A-12", "occupied": True},
    {"label": "A-13", "occupied": False},
]

adapter.post_snapshot(parking_regions_snapshot)
```

If your region objects use different keys, update the label/status extraction in [smartpark/worker.py](/Users/bytedance/personal/SmartPark/smartpark/worker.py) instead of changing the rest of the stack.
