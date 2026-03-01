#!/usr/bin/env bash
# scripts/demo.sh – One-command demo of the Manufacturing Workflow System
# Usage: bash scripts/demo.sh

set -e

API="http://localhost:8000"
SEP="──────────────────────────────────────────────────────"

echo ""
echo "🏭  Manufacturing Workflow Automation System – Demo"
echo "$SEP"

# 1. Health check
echo ""
echo "1️⃣  Health check"
curl -s "$API/health" | python3 -m json.tool

# 2. Create a station
echo ""
echo "2️⃣  Create a QA station"
curl -s -X POST "$API/stations" \
  -H "Content-Type: application/json" \
  -d '{"name":"QA-Demo","type":"QA"}' | python3 -m json.tool

# 3. Create a work order
echo ""
echo "3️⃣  Create a work order"
WO=$(curl -s -X POST "$API/work-orders" \
  -H "Content-Type: application/json" \
  -d '{"product_type":"Widget-Demo","priority":3}')
echo "$WO" | python3 -m json.tool
WO_ID=$(echo "$WO" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 4. Start the work order
echo ""
echo "4️⃣  Start work order $WO_ID"
STATION_ID=$(curl -s "$API/stations" | python3 -c "
import sys,json
stations = json.load(sys.stdin)
for s in stations:
    if s['name'] == 'QA-Demo':
        print(s['id'])
        break
")
curl -s -X POST "$API/events" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"WORK_ORDER_STARTED\",\"work_order_id\":$WO_ID}" | python3 -m json.tool

# 5. Emit a defect event
echo ""
echo "5️⃣  Emit defect event"
curl -s -X POST "$API/events" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"DEFECT_FOUND\",\"station_id\":$STATION_ID,\"work_order_id\":$WO_ID,\"payload\":{\"severity\":\"major\"}}" | python3 -m json.tool

# 6. Complete the work order
echo ""
echo "6️⃣  Complete work order"
curl -s -X POST "$API/events" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"WORK_ORDER_COMPLETED\",\"work_order_id\":$WO_ID}" | python3 -m json.tool

# 7. KPI summary
echo ""
echo "7️⃣  KPI Summary"
curl -s "$API/kpis/summary" | python3 -m json.tool

echo ""
echo "$SEP"
echo "✅  Demo complete. Visit $API/docs for the full interactive API."
echo ""
