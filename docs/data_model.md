# Data Model

## Entity Relationship Diagram

```
┌─────────────────────┐         ┌─────────────────────┐
│      WorkOrder      │         │       Station        │
├─────────────────────┤         ├─────────────────────┤
│ id         (PK)     │         │ id          (PK)     │
│ product_type        │         │ name        (UNIQUE) │
│ priority   (1–5)    │         │ type        (ENUM)   │
│ status     (ENUM)   │         │   CUTTING            │
│   PENDING           │         │   ASSEMBLY           │
│   IN_PROGRESS       │         │   QA                 │
│   ON_HOLD           │         │   PACKAGING          │
│   COMPLETED         │         │ status      (ENUM)   │
│   CANCELLED         │         │   RUNNING            │
│ created_at          │         │   IDLE               │
│ started_at          │         │   DOWN               │
│ completed_at        │         │   HOLD               │
└──────────┬──────────┘         │ last_heartbeat_at    │
           │ 1                  └──────────┬───────────┘
           │                              │ 1
           │ N           N                │ N
           └──────────┬───────────────────┘
                      │
              ┌───────▼─────────┐
              │      Event       │
              ├─────────────────┤
              │ id       (PK)   │
              │ timestamp       │
              │ type    (ENUM)  │
              │   WORK_ORDER_STARTED   │
              │   WORK_ORDER_COMPLETED │
              │   STEP_COMPLETED       │
              │   DEFECT_FOUND         │
              │   MACHINE_DOWN         │
              │   MACHINE_UP           │
              │   MACHINE_IDLE         │
              │   QA_HOLD              │
              │ station_id (FK) │
              │ work_order_id(FK)│
              │ payload  (JSON) │
              └─────────────────┘

┌─────────────────────────┐    ┌───────────────────────┐
│     AutomationRule      │    │       KPIHistory       │
├─────────────────────────┤    ├───────────────────────┤
│ id             (PK)     │    │ id           (PK)     │
│ name           (UNIQUE) │    │ timestamp             │
│ description             │    │ throughput            │
│ condition_json (JSON)   │    │ defect_rate           │
│   type: string          │    │ downtime_minutes      │
│   threshold: float      │    │ avg_cycle_time        │
│ action_json    (JSON)   │    └───────────────────────┘
│   type: string          │
│ enabled        (BOOL)   │
│ last_triggered_at       │
└─────────────────────────┘
```

## Key Indexes

| Table         | Index                                 | Purpose                            |
|---------------|---------------------------------------|------------------------------------|
| work_orders   | (status, created_at)                  | Filtered listing by status + date  |
| events        | (type, timestamp)                     | Defect rate / downtime queries     |
| events        | (station_id, timestamp)               | Per-station cycle time analysis    |
| stations      | (status)                              | Fast station health checks         |
| kpi_history   | (timestamp)                           | Time-series KPI trending           |

## JSON Schema Examples

### condition_json
```json
{"type": "defect_rate_spike", "threshold": 0.15, "sample_size": 50}
{"type": "station_downtime", "threshold_minutes": 10}
{"type": "high_cycle_time", "threshold_minutes": 30, "window_minutes": 60}
```

### action_json
```json
{"type": "hold_qa_station"}
{"type": "pause_work_orders"}
{"type": "flag_bottleneck"}
```
