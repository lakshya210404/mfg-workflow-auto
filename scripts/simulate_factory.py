#!/usr/bin/env python3
"""
scripts/simulate_factory.py

Simulate a full factory shift: create stations + work orders,
emit realistic events (step completions, defects, downtime), and
print a final KPI report.

Usage:
    python scripts/simulate_factory.py [--api-url http://localhost:8000] [--work-orders 20]
"""

import argparse
import json
import logging
import random
import sys
import time
from datetime import datetime

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("simulate")

PRODUCT_TYPES = ["Widget-A", "Widget-B", "Gear-XL", "Gear-SM", "Panel-Pro", "Bracket-HD"]
STATION_DEFINITIONS = [
    {"name": "Cutting-01", "type": "CUTTING"},
    {"name": "Cutting-02", "type": "CUTTING"},
    {"name": "Assembly-01", "type": "ASSEMBLY"},
    {"name": "Assembly-02", "type": "ASSEMBLY"},
    {"name": "QA-01", "type": "QA"},
    {"name": "Packaging-01", "type": "PACKAGING"},
]
STATION_CYCLE_TIMES = {
    "CUTTING": (8, 25),    # (min_min, max_min)
    "ASSEMBLY": (15, 45),
    "QA": (5, 20),
    "PACKAGING": (3, 10),
}


class FactorySimulator:
    """Drives the factory simulation by calling the REST API."""

    def __init__(self, api_url: str) -> None:
        self.api_url = api_url.rstrip("/")
        self.client = httpx.Client(base_url=self.api_url, timeout=10.0)
        self.station_map: dict[str, dict] = {}  # name -> station response
        self.work_order_ids: list[int] = []

    def _post(self, path: str, payload: dict) -> dict:
        resp = self.client.post(path, json=payload)
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        resp = self.client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    def setup_stations(self) -> None:
        """Register stations (skip if already exist)."""
        logger.info("Setting up stations…")
        for s_def in STATION_DEFINITIONS:
            try:
                data = self._post("/stations", s_def)
                self.station_map[data["name"]] = data
                logger.info("  Created station: %s (id=%d)", data["name"], data["id"])
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 409:
                    # Already exists – fetch it
                    stations = self._get("/stations")
                    for s in stations:  # type: ignore[union-attr]
                        if s["name"] == s_def["name"]:
                            self.station_map[s["name"]] = s
                else:
                    raise

    def create_work_orders(self, count: int) -> None:
        """Create `count` work orders with random product types and priorities."""
        logger.info("Creating %d work orders…", count)
        for i in range(count):
            payload = {
                "product_type": random.choice(PRODUCT_TYPES),
                "priority": random.randint(1, 5),
            }
            data = self._post("/work-orders", payload)
            self.work_order_ids.append(data["id"])
        logger.info("  Created work orders: %s", self.work_order_ids[:5], "…" if count > 5 else "")

    def emit_event(self, event_type: str, station_id: int | None = None,
                   work_order_id: int | None = None, payload: dict | None = None) -> dict:
        """Send a single event to the API."""
        data = self._post("/events", {
            "type": event_type,
            "station_id": station_id,
            "work_order_id": work_order_id,
            "payload": payload or {},
        })
        return data

    def run_work_order_through_stations(self, wo_id: int) -> None:
        """Simulate a work order moving through CUTTING → ASSEMBLY → QA → PACKAGING."""
        station_sequence = ["CUTTING", "ASSEMBLY", "QA", "PACKAGING"]

        # Start the work order
        self.emit_event("WORK_ORDER_STARTED", work_order_id=wo_id)

        for station_type in station_sequence:
            station = self._pick_station(station_type)
            if not station:
                continue

            station_id = station["id"]
            min_t, max_t = STATION_CYCLE_TIMES[station_type]
            duration = round(random.uniform(min_t, max_t), 1)

            # Occasionally introduce downtime (5% chance per step)
            if random.random() < 0.05:
                down_duration = random.uniform(5, 20)
                logger.warning("  ⚠️  Station %s going DOWN for %.1f min", station["name"], down_duration)
                self.emit_event("MACHINE_DOWN", station_id=station_id,
                                payload={"reason": "unplanned_stop", "duration_minutes": down_duration})
                time.sleep(0.05)  # brief pause in sim
                self.emit_event("MACHINE_UP", station_id=station_id)

            # Emit STEP_COMPLETED
            self.emit_event(
                "STEP_COMPLETED",
                station_id=station_id,
                work_order_id=wo_id,
                payload={"step": station_type, "duration_minutes": duration},
            )

            # Defect chance: 8% for QA, 3% for others
            defect_chance = 0.08 if station_type == "QA" else 0.03
            if random.random() < defect_chance:
                logger.warning("  🔴 Defect found at %s for WO %d", station["name"], wo_id)
                self.emit_event("DEFECT_FOUND", station_id=station_id, work_order_id=wo_id,
                                payload={"severity": random.choice(["minor", "major"])})

        # Complete the work order
        self.emit_event("WORK_ORDER_COMPLETED", work_order_id=wo_id)

    def _pick_station(self, station_type: str) -> dict | None:
        """Pick a random station of the given type."""
        candidates = [s for s in self.station_map.values() if s["type"] == station_type]
        return random.choice(candidates) if candidates else None

    def print_kpi_report(self) -> None:
        """Fetch and print the final KPI summary."""
        summary = self._get("/kpis/summary")
        bottlenecks = self._get("/kpis/bottlenecks")

        print("\n" + "=" * 60)
        print("  📊  FACTORY SIMULATION KPI REPORT")
        print("=" * 60)
        print(f"  Completed Work Orders : {summary['completed_work_orders']}")  # type: ignore[index]
        print(f"  Throughput (WOs/hr)   : {summary['throughput_per_hour']:.3f}")  # type: ignore[index]
        print(f"  Avg Cycle Time (min)  : {summary['avg_cycle_time_minutes']:.1f}")  # type: ignore[index]
        print(f"  Defect Rate           : {summary['defect_rate_percent']:.1f}%")  # type: ignore[index]
        print(f"  Total Downtime (min)  : {summary['total_downtime_minutes']:.1f}")  # type: ignore[index]
        print(f"  Active Stations       : {summary['active_stations']}")  # type: ignore[index]
        print(f"  Stations DOWN         : {summary['stations_down']}")  # type: ignore[index]

        bn_list = bottlenecks["bottlenecks"]  # type: ignore[index]
        if bn_list:
            print(f"\n  ⚠️  Bottlenecks ({len(bn_list)}):")
            for bn in bn_list:
                print(f"     • {bn['station_name']}: {bn['avg_cycle_time_minutes']:.1f} min avg")
                print(f"       → {bn['recommendation']}")
        else:
            print("\n  ✅ No bottlenecks detected")
        print("=" * 60 + "\n")

    def run(self, num_work_orders: int = 20) -> None:
        """Run the full simulation."""
        logger.info("🏭 Starting factory simulation (%d work orders)", num_work_orders)

        self.setup_stations()
        self.create_work_orders(num_work_orders)

        logger.info("Processing work orders through the factory…")
        for idx, wo_id in enumerate(self.work_order_ids, 1):
            logger.info("  [%d/%d] Processing WO %d", idx, len(self.work_order_ids), wo_id)
            self.run_work_order_through_stations(wo_id)

        self.print_kpi_report()
        logger.info("✅ Simulation complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate a manufacturing factory shift")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--work-orders", type=int, default=20, help="Number of work orders to simulate")
    args = parser.parse_args()

    sim = FactorySimulator(api_url=args.api_url)
    sim.run(num_work_orders=args.work_orders)


if __name__ == "__main__":
    main()
