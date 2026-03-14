from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path
from typing import Any


class SmartParkIngestAdapter:
    def __init__(self, lot_id: str) -> None:
        self.lot_id = lot_id
        self.last_sent: dict[str, str] = {}

    def build_updates(self, raw_snapshot: Any) -> list[dict[str, str]]:
        normalized = self._normalize_snapshot(raw_snapshot)
        changed_updates = []
        for label, status in normalized.items():
            if self.last_sent.get(label) == status:
                continue
            changed_updates.append(
                {
                    "lot_id": self.lot_id,
                    "label": label,
                    "status": status,
                }
            )
            self.last_sent[label] = status
        return changed_updates

    def post_snapshot(self, raw_snapshot: Any) -> dict[str, Any]:
        from smartpark.client import ingest_slot_updates

        updates = self.build_updates(raw_snapshot)
        if not updates:
            return {"updated": 0, "skipped": True}
        return ingest_slot_updates(updates)

    def _normalize_snapshot(self, raw_snapshot: Any) -> dict[str, str]:
        if isinstance(raw_snapshot, dict):
            if "slots" in raw_snapshot:
                return self._normalize_slot_list(raw_snapshot["slots"])
            return self._normalize_slot_mapping(raw_snapshot)
        if isinstance(raw_snapshot, list):
            return self._normalize_slot_list(raw_snapshot)
        raise TypeError("Snapshot must be a dict or list.")

    def _normalize_slot_mapping(self, slot_mapping: dict[str, Any]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for label, value in slot_mapping.items():
            normalized[str(label)] = self._coerce_status(value)
        return normalized

    def _normalize_slot_list(self, slots: list[Any]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for item in slots:
            if not isinstance(item, dict):
                raise TypeError("Each slot entry must be a dict.")
            label = self._extract_label(item)
            status = self._extract_status(item)
            normalized[label] = status
        return normalized

    def _extract_label(self, item: dict[str, Any]) -> str:
        for key in ("label", "slot_id", "id", "name", "region_id"):
            value = item.get(key)
            if value:
                return str(value)
        raise ValueError(f"Could not find slot label in item: {item}")

    def _extract_status(self, item: dict[str, Any]) -> str:
        if "status" in item:
            return self._coerce_status(item["status"])
        if "occupied" in item:
            return "occupied" if bool(item["occupied"]) else "free"
        if "is_occupied" in item:
            return "occupied" if bool(item["is_occupied"]) else "free"
        if "available" in item:
            return "free" if bool(item["available"]) else "occupied"
        raise ValueError(f"Could not determine status in item: {item}")

    def _coerce_status(self, value: Any) -> str:
        if isinstance(value, bool):
            return "occupied" if value else "free"
        normalized = str(value).strip().lower()
        if normalized in {"free", "available", "vacant", "open", "0"}:
            return "free"
        if normalized in {"occupied", "busy", "taken", "filled", "1"}:
            return "occupied"
        raise ValueError(f"Unsupported status value: {value}")


def load_snapshot_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def get_lot_spot_labels(lot_id: str) -> list[str]:
    from smartpark.client import load_lots

    lots = load_lots()
    for lot in lots:
        if lot["id"] == lot_id:
            return [spot["label"] for spot in lot["spots"]]
    raise ValueError(f"Unknown lot_id: {lot_id}")


def build_demo_snapshot(lot_id: str, cycle: int) -> list[dict[str, Any]]:
    labels = get_lot_spot_labels(lot_id)
    snapshot = []
    for index, label in enumerate(labels):
        occupied = (index + cycle) % 3 == 0
        snapshot.append({"label": label, "occupied": occupied})
    return snapshot


def run_file_mode(lot_id: str, input_path: Path, once: bool, poll_seconds: float) -> None:
    adapter = SmartParkIngestAdapter(lot_id)
    while True:
        raw_snapshot = load_snapshot_file(input_path)
        result = adapter.post_snapshot(raw_snapshot)
        print(json.dumps({"mode": "file", "result": result}, indent=2))
        if once:
            return
        time.sleep(poll_seconds)


def run_demo_mode(lot_id: str, cycles: int, poll_seconds: float) -> None:
    adapter = SmartParkIngestAdapter(lot_id)
    for cycle in range(cycles):
        raw_snapshot = build_demo_snapshot(lot_id, cycle)
        result = adapter.post_snapshot(raw_snapshot)
        print(
            json.dumps(
                {
                    "mode": "demo",
                    "cycle": cycle + 1,
                    "result": result,
                    "snapshot": raw_snapshot,
                },
                indent=2,
            )
        )
        if cycle < cycles - 1:
            time.sleep(poll_seconds)


def run_random_mode(lot_id: str, cycles: int, poll_seconds: float) -> None:
    adapter = SmartParkIngestAdapter(lot_id)
    labels = get_lot_spot_labels(lot_id)
    for cycle in range(cycles):
        raw_snapshot = [{"label": label, "occupied": random.choice([True, False])} for label in labels]
        result = adapter.post_snapshot(raw_snapshot)
        print(
            json.dumps(
                {
                    "mode": "random",
                    "cycle": cycle + 1,
                    "result": result,
                },
                indent=2,
            )
        )
        if cycle < cycles - 1:
            time.sleep(poll_seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SmartPark worker adapter for YOLO/ParkingManagement output.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    file_parser = subparsers.add_parser("from-file", help="Read a JSON snapshot and ingest it.")
    file_parser.add_argument("--lot-id", required=True)
    file_parser.add_argument("--input", required=True, type=Path)
    file_parser.add_argument("--once", action="store_true")
    file_parser.add_argument("--poll-seconds", type=float, default=5.0)

    demo_parser = subparsers.add_parser("demo", help="Generate deterministic demo occupancy cycles.")
    demo_parser.add_argument("--lot-id", required=True)
    demo_parser.add_argument("--cycles", type=int, default=5)
    demo_parser.add_argument("--poll-seconds", type=float, default=3.0)

    random_parser = subparsers.add_parser("random", help="Generate random occupancy cycles for shakeout testing.")
    random_parser.add_argument("--lot-id", required=True)
    random_parser.add_argument("--cycles", type=int, default=5)
    random_parser.add_argument("--poll-seconds", type=float, default=3.0)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "from-file":
        run_file_mode(args.lot_id, args.input, args.once, args.poll_seconds)
        return
    if args.command == "demo":
        run_demo_mode(args.lot_id, args.cycles, args.poll_seconds)
        return
    if args.command == "random":
        run_random_mode(args.lot_id, args.cycles, args.poll_seconds)
        return
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
