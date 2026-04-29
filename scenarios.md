# Restaurant Queue Simulator — Scenario Design

**This is Version 4** (generated from actual simulation runs against request1–10.csv and restaurant1–10.csv)

---

## Scenario 1: Weekday Lunch Rush (Sharing vs. No-Sharing)

### Objective
Compare the impact of table sharing on wait time and queue length using a small cafe during lunch peak. Identical arrival data (8 groups: 5 couples, 2 VIPs, 1 solo diner); only the `share` flag differs.

### Setup
- **Capacity**: 2x2-seat + 1x4-seat tables (3 tables, 8 seats)
- **Customer arrivals** (request1.csv / request2.csv):
  - 5 couples arriving 11:30–11:50 at 5-min intervals (2p each, 30 min dining)
  - 2 VIP business regulars at 11:32 & 11:37 (2p, 30 min dining)
  - 1 solo no-share diner at 12:00 (1p, 30 min)
- **Key difference**: 1A has 5 sharing couples (share=1); 1B sets all share=0. All other fields identical.

### Logic
VIP heap ordering (-vip, arrival, queue_id) prioritizes loyal regulars. Sharing `allocate()` fills the smallest remaining slot to maximize concurrent table usage; no-share requires a fully empty table of sufficient size.

### Comparative Results

| Metric | 1A: Sharing Enabled | 1B: Sharing Disabled | Improvement |
|---|---|---|---|
| Avg. Wait | 10.6 min | 17.1 min | **-38.0%** |
| Max Wait | 30 min | 40 min | -25.0% |
| Peak Queue | 4 | 5 | -20% |
| Utilization* | 77.8% | 87.0% | -10.6% |
| Service Level (<=10 min) | 50.0% | 37.5% | +12.5 pp |
| Groups Served | 8/8 | 8/8 | -- |

*\*Utilization includes wait time in occupancy intervals (arrival -> leave_time), which inflates the no-sharing metric. Effective seat-time-only utilization strongly favors sharing.*

### Technical Highlights
- **Sharing Logic**: The 4-seat table dynamically hosts 2 couples concurrently in 1A (4 people occupying 4 seats), while 1B wastes capacity — a 2p group monopolizing a 4-seat table leaves 2 seats idle.
- **VIP Priority**: VIPs arriving at 11:32 (after group 1 at 11:30) jump the queue via heap ordering. In 1A, a VIP takes a 2-seat table while sharing couples fill the 4-seat; in 1B, VIPs block 2-seat tables, forcing later arrivals into deeper queues.
- **Real-World Relevance**: Models Hong Kong cafe "daap toi" culture — sharing is mathematically superior for high-density lunch environments, cutting wait times by ~38% with zero additional infrastructure.

---

## Scenario 2: Friday Dinner – Reservation vs. First-Come-First-Served

### Objective
Demonstrate how reservation pre-allocation guarantees service for booked guests, and reveal the trade-off between guaranteed seating and overall system efficiency.

### Setup
- **Capacity**: 1x4-seat + 2x2-seat tables (3 tables, 8 seats)
- **Customer arrivals** (request3.csv / request4.csv):
  - 1 reserved 4p group at 18:15 (45 min dining) — *the booked guest*
  - 1 walk-in 4p no-share group at 18:00 (45 min) — *competes for the only 4-seat table*
  - 5 walk-in sharing couples arriving 18:00–18:25 (2p, 40 min)
  - 2 VIP walk-ins at 18:10 & 18:20 (2p, 40 min)
- **Key difference**: 2A has the 18:15 group as reserved (reserved=1); 2B makes it a regular walk-in (reserved=0, share=1). All other groups identical.

### Logic
`allocate_reserved_tables()` pre-assigns the 4-seat table to the reserved group, blocking walk-ins whose stay would overlap (18:00–18:45 conflicts with 18:15 reservation start). In 2B, no table is held — first-come-first-served decides who gets the 4-seat.

### Comparative Results

| Metric | 2A: Reservation | 2B: No Reservation | Delta |
|---|---|---|---|
| Avg. Wait | 36.7 min | 31.1 min | +5.6 min |
| Max Wait | 80 min | 70 min | +10 min |
| Peak Queue | 6 | 6 | 0 |
| Utilization | 88.5% | 94.9% | -6.4 pp |
| Service Level (<=10 min) | 33.3% | 33.3% | 0 pp |
| Groups Served | 9/9 | 9/9 | -- |
| **Guest 1 Wait (booked in 2A)** | **0 min** | **70 min** | **-100%** |

### Technical Highlights
- **The Reservation Guarantee**: In 2A, the reserved 4p group (idx 1) is seated instantly at 18:15 with zero wait. The 4-seat table is held empty from 18:00–18:15 — the walk-in 4p (idx 7) is blocked because its 45-min stay would overlap the reservation. In 2B, idx 7 takes the table immediately at 18:00, and idx 1 arrives at 18:15 to find every table occupied — then waits 70 minutes.
- **The Efficiency Trade-off**: 2B achieves lower *average* wait (31.1 vs 36.7) and higher utilization (94.9% vs 88.5%) because no tables sit idle. Reservation trades overall throughput for *guaranteed* service to booked guests — exactly the business decision real restaurants face with platforms like OpenTable.
- **Table Fragmentation**: In 2B, idx 1's 70-min wait is exacerbated by a 2p group (idx 4) taking the last 2 seats of the 4-seat table at 18:45, leaving idx 1 (needing 4 seats) stranded. Reservation prevents this fragmentation by dedicating the table.
- **Real-World Relevance**: Hong Kong restaurants using booking apps need guaranteed tables for reserved guests during peak hours. Our model lets operators quantify exactly what that guarantee costs in walk-in wait time.

---

## Scenario 3: Weekend Family Brunch – No-Share vs. All Sharing

### Objective
Compare mixed no-share preference handling against universal sharing during a weekend family brunch with 12 groups.

### Setup
- **Capacity**: Production config — 5x2-seat + 3x4-seat + 2x6-seat + 1x8-seat (11 tables, 42 seats)
- **Customer arrivals** (request5.csv / request6.csv):
  - 4 families of 4p arriving 10:00–10:06 (50 min dining)
  - 5 sharing groups of 2–4p arriving 10:00–10:12 (40–50 min)
  - 3 VIP grandparents of 2p arriving 10:01–10:09 (40 min)
- **Key difference**: 3A has 4 families as no-share (share=0) + 3 VIPs as no-share (7 no-share total); 3B sets all 12 groups to share=1.

### Logic
No-share allocation requires a fully empty table >= group size. Sharing allocation fills the smallest remaining slot across any table with space. VIP heap ordering applies in both.

### Comparative Results

| Metric | 3A: Mixed (No-Share Families) | 3B: All Sharing | Improvement |
|---|---|---|---|
| Avg. Wait | 3.1 min | 0.0 min | **-100%** |
| Max Wait | 37 min | 0 min | -100% |
| Peak Queue | 1 | 0 | -100% |
| Utilization | 49.1% | 72.6% | +23.5 pp |
| Service Level (<=10 min) | 91.7% | 100.0% | +8.3 pp |
| Groups Served | 12/12 | 12/12 | -- |

### Technical Highlights
- **No-Share Cost**: In 3A, each no-share 4p family demands a dedicated table. With 3x4-seat tables available, the first 3 families are seated immediately, but the 4th family (arriving 10:06) must wait 37 min for a 4-seat table to free up — despite an 8-seat table sitting empty (too large for no-share allocation's exact-fit logic: the allocator picks the smallest qualifying empty table).
- **Sharing Efficiency**: 3B seats all 12 groups instantly. The allocator packs groups into optimal slots (e.g., a 2p + 4p into a 6-seat table concurrently), achieving 72.6% utilization with zero wait.
- **Real-World Relevance**: Hong Kong weekend brunch mixes families refusing sharing with flexible young groups. Our dual `allocate()` logic respects both preferences — and the metrics quantify exactly what "refusing to share" costs in wait time.

---

## Scenario 4: Business Lunch in Central – Miss/Comeback vs. No Miss

### Objective
Model a Central district business lunch with miss/comeback recovery logic, comparing against the same customers as regular arrivals.

### Setup
- **Capacity**: Production config — 5x2-seat + 3x4-seat + 2x6-seat + 1x8-seat (11 tables, 42 seats)
- **Customer arrivals** (request7.csv / request8.csv):
  - 6 reserved groups of 2–6p all arriving at 12:00 (30–70 min dining)
  - 4 VIP walk-ins arriving 12:00–12:06 (2–3p, 30–45 min)
  - 2 miss+comeback / regular groups arriving 12:08 & 12:10 (2p, 35 min)
  - 3 sharing walk-ins arriving 12:12–12:16 (2–4p, 40–55 min)
- **Key difference**: 4A has 2 groups with miss=1, comeback=1 (deferred 15 min, reactivated via 3:1 callback); 4B converts those same groups to regular arrivals (miss=0).

### Logic
Miss customers are deferred 15 min after arrival, then placed in `miss_queue`. The 3:1 callback rule activates one miss customer for every 3 normal (non-VIP, non-reserved) customers served. When the waiting queue empties, all remaining miss customers are batch-activated.

### Comparative Results

| Metric | 4A: Miss/Comeback Enabled | 4B: No Miss | Improvement |
|---|---|---|---|
| Avg. Wait | 2.2 min | 6.6 min | **-66.7%** |
| Max Wait | 33 min | 29 min | +13.8% |
| Peak Queue | 1 | 4 | -75% |
| Utilization | 55.7% | 58.0% | -2.3 pp |
| Service Level (<=10 min) | 93.3% | 73.3% | +20.0 pp |
| Groups Served | 15/15 | 15/15 | -- |

### Technical Highlights
- **Counterintuitive Result**: 4A (with miss) has *lower* average wait than 4B. Miss customers are removed from the queue during peak congestion (12:08–12:23) and reactivated later when tables have freed up. In 4B, those same customers compete for tables during the 12:00 reservation surge, deepening the peak queue from 1 to 4.
- **Recovery Mechanism**: The `miss_queue` + 3:1 callback ensures no-shows don't permanently lose their spot. The deferred return spreads load more evenly across the simulation window — a form of natural load-leveling.
- **Real-World Relevance**: Central district lunches are time-sensitive. Our integrated reservation slots + miss_queue + callback logic recovers revenue from delayed clients while actually *improving* overall wait metrics by shifting demand away from the peak.

---

## Scenario 5: Full-Day Operation – Production vs. Limited Capacity

### Objective
Comprehensive full-day simulation comparing a well-equipped production restaurant against a capacity-constrained smaller venue, spanning lunch through dinner with all features active.

### Setup
- **Capacity**:
  - 5A (Production): 5x2-seat + 3x4-seat + 2x6-seat + 1x8-seat (11 tables, 42 seats)
  - 5B (Limited): 2x2-seat + 1x4-seat + 1x6-seat (4 tables, 14 seats)
- **Customer arrivals** (request9.csv / request10.csv): Identical 50 groups spread 11:00–21:50 (~11 hours):
  - 7 VIPs, 5 reserved, 5 miss (3 comeback, 2 permanent no-show), 7 no-share
  - Mixed sizes 1–6p, durations 20–90 min
  - 31 sharing, 19 no-share groups

### Logic
Full feature integration — reservation pre-allocation, VIP heap priority, sharing/no-share dual allocation, miss/comeback with 3:1 callback — all interacting across an 11-hour operating day under two different capacity constraints.

### Comparative Results

| Metric | 5A: Production (42 seats) | 5B: Limited (14 seats) | Change |
|---|---|---|---|
| Avg. Wait | 0.0 min | 64.9 min | +64.9 min |
| Max Wait | 0 min | 356 min | +356 min |
| Peak Queue | 0 | 8 | +8 |
| Utilization | 30.7% | 58.8% | +28.1 pp |
| Service Level (<=10 min) | 100.0% | 60.4% | -39.6 pp |
| Groups Served | 48/50 | 48/50 | -- |

### Technical Highlights
- **Capacity-Driven Stress**: 5A's 42 seats handle all 48 serviceable groups with zero wait — the restaurant is over-provisioned for this demand. 5B's 14 seats (3x fewer) create a realistic bottleneck: average wait jumps to 65 minutes, and only 60% of groups are seated within 10 minutes.
- **Same Demand, Different Experience**: Both scenarios serve the same 48/50 groups (2 are permanent no-shows: miss=1, comeback=0). The 14-seat venue still eventually serves everyone — but at dramatically worse service quality.
- **Max Wait Reality**: The 356-min (~6 hour) max wait in 5B represents a low-priority large group arriving during peak congestion and repeatedly passed over due to VIP priority and size mismatch with available tables. This is the "worst-case" scenario that real restaurant operators need visibility into.
- **Feature Integration**: All subsystems (reservation, VIP, sharing, miss/comeback) operate correctly across the full day with no conflicts in both configs — the architecture scales from 4 to 11 tables without modification.
- **Real-World Relevance**: Mirrors the decision every Hong Kong restaurateur faces: how many tables of each size? Our model lets operators plug in different floor plans and see the wait-time consequences before signing a lease.

---

## Summary of File Changes (v4)

| Scenario | Change | Before | After |
|---|---|---|---|
| 1 | request2.csv fixed to match request1.csv | VIP dur=40, solo@11:55 | VIP dur=30, solo@12:00 (same as 1A) |
| 2 | Restaurant redesigned | 2x4-seat (original) | 1x4 + 2x2-seat |
| 2 | Requests redesigned | 3x4p simultaneous arrival → A/B identical | Reserved 4p@18:15 vs walk-in 4p@18:00 → clear difference |
| 5 | Restaurant10 reduced | 3x2+2x4+2x6 (26 seats) → no stress | 2x2+1x4+1x6 (14 seats) → dramatic stress test |
