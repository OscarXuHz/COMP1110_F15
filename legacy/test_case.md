# Test Cases for Restaurant Queue Simulation

Run all tests: `python3 run_tests.py`

CSV format: `index, people, arrival(YYYYMMDDHHMMSS), duration, share, miss, comeback, vip, reserved`

---

## Test 1: Sanity Check — Single Customer, Single Table

**Purpose:** Verify basic flow: one customer arrives, sits immediately, leaves.

**Restaurant:** 1 table × 4 seats

**Requests:**

| # | People | Arrival | Dur | Share | Miss | Comeback | VIP | Reserved |
|---|--------|---------|-----|-------|------|----------|-----|----------|
| 1 | 2      | 12:00   | 30  | 1     | 0    | 0        | 0   | 0        |

**Manual Trace:**
- T+0: Customer 1 arrives (2 ppl). Table 0 (cap=4) available, remaining=4 ≥ 2. Seated. Wait=0. Leaves T+30.
- T+30: Customer 1 leaves. Simulation ends.
- table_busy_time[0]=30, total_time=30. Utilization = (30/1)/30 = 100%.
- Service level: wait=0 ≤ 10 → 1/1 = 100%.

**Expected Output:**
```
Average Wait Time: 0.0 min
Max Wait Time: 0 min
Peak Queue Length: 0
Groups Served: 1
Table Utilization: 100.0%
Service Level: 100.0%
Total Time: 30 min
```

**Result: PASS** ✓

---

## Test 2: VIP Priority — VIP Jumps the Queue

**Purpose:** When multiple customers wait, VIP is placed at the front of the waiting queue and served before earlier-arriving normal customers.

**Restaurant:** 1 table × 2 seats

**Requests:**

| # | People | Arrival | Dur | Share | Miss | Comeback | VIP | Reserved |
|---|--------|---------|-----|-------|------|----------|-----|----------|
| 1 | 2      | 12:00   | 30  | 1     | 0    | 0        | 0   | 0        |
| 2 | 2      | 12:05   | 30  | 1     | 0    | 0        | 0   | 0        |
| 3 | 2      | 12:10   | 30  | 1     | 0    | 0        | 1   | 0        |

**Manual Trace:**
- T+0: C1 seated. Table full.
- T+5: C2 arrives, no space → queue=[C2].
- T+10: C3 arrives (VIP), no space → inserted at front. queue=[C3, C2].
- T+30: C1 leaves. C3 (VIP) popped first → seated. Wait=20. Leave T+60.
  - C2 cannot be seated (table full) → put back. queue=[C2].
- T+60: C3 leaves. C2 seated. Wait=55. Leave T+90.
- Waits: 0, 55, 20. Avg=(0+55+20)/3=25.0. Max=55.
- table_busy_time=90, total=90. Util=100%.
- Service level: only C1 (wait=0 ≤ 10) → 1/3 = 33.3%.

**Expected Output:**
```
Average Wait Time: 25.0 min
Max Wait Time: 55 min
Peak Queue Length: 2
Groups Served: 3
Table Utilization: 100.0%
Service Level: 33.3%
Total Time: 90 min
```

**Result: PASS** ✓

---

## Test 3: Table Sharing — Multiple Groups on One Table

**Purpose:** Verify that groups willing to share can be seated concurrently at the same table.

**Restaurant:** 1 table × 6 seats

**Requests:**

| # | People | Arrival | Dur | Share | Miss | Comeback | VIP | Reserved |
|---|--------|---------|-----|-------|------|----------|-----|----------|
| 1 | 2      | 12:00   | 30  | 1     | 0    | 0        | 0   | 0        |
| 2 | 2      | 12:02   | 30  | 1     | 0    | 0        | 0   | 0        |
| 3 | 2      | 12:05   | 30  | 1     | 0    | 0        | 0   | 0        |

**Manual Trace:**
- T+0: C1 seated (cur=2/6). Wait=0.
- T+2: C2 seated (cur=4/6). Wait=0.
- T+5: C3 seated (cur=6/6). Wait=0.
- All groups leave at T+30, T+32, T+35 respectively.
- table_busy_time[0] = 30+30+30 = 90.
- total_time = 35. Util = (90/1)/35 = 257.1%.
- **Note:** Utilization exceeds 100% because `table_busy_time` sums per-customer durations, so shared occupancy double-counts.

**Expected Output:**
```
Average Wait Time: 0.0 min
Max Wait Time: 0 min
Peak Queue Length: 0
Groups Served: 3
Table Utilization: 257.1%
Service Level: 100.0%
Total Time: 35 min
```

**Result: PASS** ✓ (reveals utilization metric anomaly when table sharing is used)

---

## Test 4: Reservation System — Reserved Tables Held

**Purpose:** Verify reserved customers get pre-allocated tables that are blocked from other customers via `reserved_slots`.

**Restaurant:** 1 table × 4 seats, 1 table × 2 seats

**Requests:**

| # | People | Arrival | Dur | Share | Miss | Comeback | VIP | Reserved |
|---|--------|---------|-----|-------|------|----------|-----|----------|
| 1 | 3      | 12:00   | 45  | 1     | 0    | 0        | 0   | 1        |
| 2 | 2      | 12:05   | 30  | 1     | 0    | 0        | 0   | 0        |

**Manual Trace:**
- Reservation allocation: C1 (3 ppl) → Table 0 (cap=4). Reserved slot [T, T+45].
- T+0: C1 arrives (reserved). Table 0 free of customers → seated. Wait=0. Leaves T+45.
- T+5: C2 arrives. Table 0: reserved_slot [T,T+45] overlaps [T+5,T+35] → blocked. Table 1 (cap=2): free, remaining=2 ≥ 2 → seated. Wait=0. Leaves T+35.
- table_busy: [0]=45, [1]=30. Avg = 75/2 = 37.5. Util = 37.5/45 = 83.3%.

**Expected Output:**
```
Average Wait Time: 0.0 min
Max Wait Time: 0 min
Peak Queue Length: 0
Groups Served: 2
Table Utilization: 83.3%
Service Level: 100.0%
Total Time: 45 min
```

**Result: PASS** ✓

---

## Test 5: Miss & Comeback — 3:1 Callback Ratio

**Purpose:** Verify the miss/comeback mechanism. Missed customers enter `miss_queue` and are called back after every 3 normal customers are served.

**Restaurant:** 1 table × 2 seats

**Requests:**

| # | People | Arrival | Dur | Share | Miss | Comeback | VIP | Reserved |
|---|--------|---------|-----|-------|------|----------|-----|----------|
| 1 | 2      | 12:00   | 20  | 1     | 1    | 1        | 0   | 0        |
| 2 | 2      | 12:02   | 20  | 1     | 0    | 0        | 0   | 0        |
| 3 | 2      | 12:04   | 20  | 1     | 0    | 0        | 0   | 0        |
| 4 | 2      | 12:06   | 20  | 1     | 0    | 0        | 0   | 0        |
| 5 | 2      | 12:08   | 20  | 1     | 0    | 0        | 0   | 0        |

**Manual Trace:**
- T+0: C1 (miss=1) → miss_queue=[C1].
- T+2: C2 seated. normal_count=1. Leave T+22.
- T+4: C3 arrives, no space → queue=[C3].
- T+6: C4 → queue=[C3,C4].
- T+8: C5 → queue=[C3,C4,C5].
- T+22: C2 leaves. C3 seated (wait=18), normal_count=2. C4 can't seat → queue=[C4,C5].
- T+42: C3 leaves. C4 seated (wait=36), normal_count=3 → **3%3==0**: pop C1 from miss_queue, comeback=1 → append to queue. queue=[C5,C1]. C5 can't seat.
- T+62: C4 leaves. C5 seated (wait=54), normal_count=4. C1 can't seat → queue=[C1].
- T+82: C5 leaves. C1 seated (wait=82), normal_count=5. Leave T+102.
- Waits: 0, 18, 36, 54, 82. Avg=38.0, Max=82.

**Expected Output:**
```
Average Wait Time: 38.0 min
Max Wait Time: 82 min
Peak Queue Length: 3
Groups Served: 5
Table Utilization: 98.0%
Service Level: 20.0%
Total Time: 102 min
```

**Result: PASS** ✓

---

## Test 6: No-Share — Exact Table Match on Arrival

**Purpose:** Verify non-sharing customers require an exact table size match. **Also exposes a code inconsistency:** the arrival handler requires `max_people == people` (strict), but the leave handler allows `max_people == people + 1` (relaxed).

**Restaurant:** 1 table × 2 seats, 1 table × 4 seats

**Requests:**

| # | People | Arrival | Dur | Share | Miss | Comeback | VIP | Reserved |
|---|--------|---------|-----|-------|------|----------|-----|----------|
| 1 | 3      | 12:00   | 30  | 0     | 0    | 0        | 0   | 0        |
| 2 | 2      | 12:02   | 30  | 0     | 0    | 0        | 0   | 0        |

**Manual Trace:**
- T+0: C1 (3 ppl, no share). Candidates: Table 1 (cap=4, ≥3). But arrival check: `max_people == people` → 4 ≠ 3 → **NOT seated**. Queue=[C1].
- T+2: C2 (2 ppl, no share). Table 0 (cap=2): cur=0, max=2==2 → seated. Wait=0. Leave T+32.
- T+32: C2 leaves. Pop C1 from queue. Table 1 (cap=4): leave check: `max == people+1` → 4 == 4 → **seated from queue**. Wait=32. Leave T+62.
- **Key finding:** C1 cannot be seated on arrival (exact match) but CAN be seated from the queue (allows +1). This inconsistency means 3-person no-share groups are penalized on arrival.

**Expected Output:**
```
Average Wait Time: 16.0 min
Max Wait Time: 32 min
Peak Queue Length: 1
Groups Served: 2
Table Utilization: 48.4%
Service Level: 50.0%
Total Time: 62 min
```

**Result: PASS** ✓ (exposes arrival vs. leave handler inconsistency)

---

## Test 7: Queue Stress — Sequential Serving Under Pressure

**Purpose:** Stress test with 5 full-table groups arriving rapidly at a single table. Tests queue ordering and sequential service.

**Restaurant:** 1 table × 4 seats

**Requests:**

| # | People | Arrival | Dur | Share | Miss | Comeback | VIP | Reserved |
|---|--------|---------|-----|-------|------|----------|-----|----------|
| 1 | 4      | 12:00   | 20  | 1     | 0    | 0        | 0   | 0        |
| 2 | 4      | 12:02   | 20  | 1     | 0    | 0        | 0   | 0        |
| 3 | 4      | 12:04   | 20  | 1     | 0    | 0        | 0   | 0        |
| 4 | 4      | 12:06   | 20  | 1     | 0    | 0        | 0   | 0        |
| 5 | 4      | 12:08   | 20  | 1     | 0    | 0        | 0   | 0        |

**Manual Trace:**
- T+0: C1 seated (4/4). Leave T+20.
- T+2,4,6,8: C2-C5 arrive, table full. queue=[C2,C3,C4,C5].
- T+20: C1 leaves. C2 seated (wait=18). Leave T+40. Queue=[C3,C4,C5].
- T+40: C2 leaves. C3 seated (wait=36). Queue=[C4,C5].
- T+60: C3 leaves. C4 seated (wait=54). Queue=[C5].
- T+80: C4 leaves. C5 seated (wait=72). Leave T+100.
- Wait pattern: 0, 18, 36, 54, 72 (linear increase of 18 min per position).

**Expected Output:**
```
Average Wait Time: 36.0 min
Max Wait Time: 72 min
Peak Queue Length: 4
Groups Served: 5
Table Utilization: 100.0%
Service Level: 20.0%
Total Time: 100 min
```

**Result: PASS** ✓

---

## Test 8: Multiple Reservations — Concurrent Bookings

**Purpose:** Two reservations at the exact same time, each needing a full table. Tests multi-table reservation allocation without conflicts.

**Restaurant:** 2 tables × 4 seats each

**Requests:**

| # | People | Arrival | Dur | Share | Miss | Comeback | VIP | Reserved |
|---|--------|---------|-----|-------|------|----------|-----|----------|
| 1 | 4      | 12:00   | 60  | 1     | 0    | 0        | 0   | 1        |
| 2 | 4      | 12:00   | 60  | 1     | 0    | 0        | 0   | 1        |
| 3 | 4      | 12:10   | 30  | 1     | 0    | 0        | 0   | 0        |

**Manual Trace:**
- Reservation: C1 → Table 0, slot [T, T+60]. C2 → Table 1, slot [T, T+60].
- T+0: C1 seated at Table 0. C2 seated at Table 1. Both wait=0.
- T+10: C3 arrives. Both tables reserved [T,T+60] overlaps [T+10,T+40] → blocked. Queue=[C3].
- T+60: C1 leaves (first, lower event counter). Pop C3. Table 0 free, reserved_slot end T+60 ≤ T+60 → no conflict. Seated. Wait=50.
- table_busy: [0]=60+30=90, [1]=60. Avg=75. Util=75/90=83.3%.

**Expected Output:**
```
Average Wait Time: 16.7 min
Max Wait Time: 50 min
Peak Queue Length: 1
Groups Served: 3
Table Utilization: 83.3%
Service Level: 66.7%
Total Time: 90 min
```

**Result: PASS** ✓

---

## Test 9: Mixed Features — All Mechanisms Combined

**Purpose:** Comprehensive test combining VIP priority, reservation, miss/comeback, table sharing, and no-share in a single scenario.

**Restaurant:** 2 tables × 2, 1 table × 4, 1 table × 6 (4 tables total)

**Requests:**

| # | People | Arrival | Dur | Share | Miss | Comeback | VIP | Reserved |
|---|--------|---------|-----|-------|------|----------|-----|----------|
| 1 | 2      | 12:00   | 30  | 1     | 0    | 0        | 1   | 0        |
| 2 | 4      | 12:00   | 40  | 1     | 0    | 0        | 0   | 1        |
| 3 | 2      | 12:03   | 25  | 1     | 1    | 1        | 0   | 0        |
| 4 | 6      | 12:05   | 50  | 1     | 0    | 0        | 0   | 0        |
| 5 | 2      | 12:10   | 20  | 0     | 0    | 0        | 0   | 0        |
| 6 | 2      | 12:15   | 30  | 1     | 0    | 0        | 1   | 0        |
| 7 | 3      | 12:20   | 35  | 1     | 0    | 0        | 0   | 0        |
| 8 | 2      | 12:25   | 25  | 1     | 0    | 0        | 0   | 0        |

**Manual Trace:**
- Reservation: C2 (4 ppl) → Table 2 (cap=4).
- T+0: C1 (VIP, share) → Table 0 (cap=2). Wait=0.
- T+0: C2 (reserved) → Table 2. Wait=0. normal_count=1.
- T+3: C3 (miss=1, comeback=1) → miss_queue=[C3].
- T+5: C4 (6 ppl) → Table 3 (cap=6). Wait=0. normal_count=2.
- T+10: C5 (no share, 2 ppl) → Table 1 (cap=2, exact). Wait=0. normal_count=3 → **callback**: pop C3, append to queue. Queue=[C3].
- T+15: C6 (VIP) → no free tables. VIP front → Queue=[C6, C3].
- T+20: C7 → no free tables → Queue=[C6, C3, C7].
- T+25: C8 → Queue=[C6, C3, C7, C8].
- T+30: C1 & C5 leave. C6 seated (wait=15). C3 seated at Table 1 (wait=27). Queue=[C7, C8].
- T+40: C2 leaves. C7 seated at Table 2 (wait=20). C8 can't fit → Queue=[C8].
- T+55: C4 & C3 leave. C8 seated at Table 3 (wait=30).
- All 8 groups served. Waits: 0,0,27,0,0,15,20,30.

**Expected Output:**
```
Average Wait Time: 11.5 min
Max Wait Time: 30 min
Peak Queue Length: 4
Groups Served: 8
Table Utilization: 79.7%
Service Level: 50.0%
Total Time: 80 min
```

**Result: PASS** ✓

---

## Test 10: Large Scale Stress Test — 50 Customers

**Purpose:** Stress test with 50 customers across 11 tables (5×2, 3×4, 2×6, 1×8 = 42 seats). Tests system performance with a mix of VIP (7), reserved (5), miss (5, 3 comeback), and no-share (7) customers over a ~2-hour arrival window.

**Restaurant:** 5 tables × 2, 3 tables × 4, 2 tables × 6, 1 table × 8 (same as production config)

**Requests:** 50 customers arriving every 2–3 minutes from 11:00 to 13:03.

| Feature | Count | Details |
|---------|-------|---------|
| VIP | 7 | Customers 3, 8, 14, 21, 27, 34, 42 |
| Reserved | 5 | Customers 5, 11, 17, 25, 41 |
| Miss (comeback) | 3 | Customers 6, 20, 30 |
| Miss (no comeback) | 2 | Customers 13, 39 — **permanently lost** |
| No-share | 7 | Customers 5, 10, 18, 24, 29, 36, 44 |
| Party size 8 | 2 | Customers 9, 33 |
| Party size 6 | 4 | Customers 4, 16, 26, 38, 47 |

**Key observations:**
- **Groups served = 48** out of 50. The 2 lost are customers 13 and 39 (miss + no comeback).
- **Max wait = 230 min** — extreme wait under sustained load.
- **Peak queue = 19** — heavy congestion during peak hours.
- **52.1% service level** — about half of customers waited >10 min.
- **51.9% utilization** — moderate, because large tables (6, 8) are often idle between large-party arrivals.
- Normal_served_count triggers callbacks for C6 (at count=3), C20 (at count=6), C30 (at count=9). C13 and C39 are popped from miss_queue but have comeback=0, so they are discarded.

**Expected Output:**
```
Average Wait Time: 64.6 min
Max Wait Time: 230 min
Peak Queue Length: 19
Groups Served: 48
Table Utilization: 51.9%
Service Level: 52.1%
Total Time: 426 min
```

**Result: PASS** ✓

---

## Summary

| Test | Focus | Served | Avg Wait | Max Wait | Queue | Util | Service Level | Status |
|------|-------|--------|----------|----------|-------|------|---------------|--------|
| 1 | Sanity check | 1 | 0.0 | 0 | 0 | 100.0% | 100.0% | ✓ |
| 2 | VIP priority | 3 | 25.0 | 55 | 2 | 100.0% | 33.3% | ✓ |
| 3 | Table sharing | 3 | 0.0 | 0 | 0 | 257.1%* | 100.0% | ✓ |
| 4 | Reservation | 2 | 0.0 | 0 | 0 | 83.3% | 100.0% | ✓ |
| 5 | Miss/comeback | 5 | 38.0 | 82 | 3 | 98.0% | 20.0% | ✓ |
| 6 | No-share match | 2 | 16.0 | 32 | 1 | 48.4% | 50.0% | ✓ |
| 7 | Queue stress | 5 | 36.0 | 72 | 4 | 100.0% | 20.0% | ✓ |
| 8 | Multi-reservation | 3 | 16.7 | 50 | 1 | 83.3% | 66.7% | ✓ |
| 9 | Mixed features | 8 | 11.5 | 30 | 4 | 79.7% | 50.0% | ✓ |
| 10 | Large scale (50) | 48 | 64.6 | 230 | 19 | 51.9% | 52.1% | ✓ |

*\* Test 3 utilization > 100% due to table_busy_time summing per-customer durations on shared tables.*

## Notable Findings

1. **Test 3 — Utilization metric anomaly:** When table sharing occurs, `table_busy_time` sums each customer's `duration` independently. Three 30-min groups on the same table yields `busy_time=90` but only 35 min elapsed, giving 257% utilization. Consider tracking per-table occupied time spans instead.

2. **Test 6 — Arrival vs. Leave handler inconsistency:** The arrival handler requires `max_people == people` for no-share customers (exact match), while the leave handler allows `max_people == people + 1`. This means a 3-person no-share group cannot be seated at a 4-person table on arrival but can be seated from the queue. Consider making both handlers consistent.
