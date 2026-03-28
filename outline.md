# Topic C: Restaurant Queue Simulation — Project Outline
**COMP 1110 Group F15**
Gao Junhang · Liu Haojie · Xu Jiahang · Yan Weibo · Zhou Bocheng

---

## 1. Task Breakdown & Role Assignment

### 1.1 Task Breakdown
- Research and Analysis
- Coding
- Case Study / Scenario and Video Demo
- Group Final Report

### 1.2 Role Assignment
| Member | Responsibilities |
|---|---|
| Liu Haojie | Research and Analysis + Coding |
| Gao Junhang | Coding + Case Study / Video Demo |
| Yan Weibo | Research + Final Report |
| Zhou Bocheng | Case Study / Video Demo + Final Report |
| Xu Jiahang | Research and Analysis + Coding |

---

## 2. Scope and Assumptions

### 2.1 Project Scope
**In Scope:**
- Load restaurant configs (table capacities, queue size ranges) and customer arrival scenarios from input files
- Simulate queuing and seating under multiple strategies:
  - Single queue
  - Size-based queues
  - Variations in queue granularity
- Compute metrics: avg/max wait time, peak queue length, table utilization, groups served, service level
- Compare paired scenarios (one variable changed at a time)
- Output results in readable text format

**Out of Scope:**
- Real-time simulation
- Graphical interfaces
- Reservation systems
- Customer walkaway behavior
- Cloud storage

### 2.2 Assumptions

#### 2.2.1 Customer Behavior
- Groups arrive exactly at their specified time (no randomness)
- Groups may abandon the queue after joining
- Dining duration is fixed and known at arrival
- Groups always accept the first suitable table offered
- Each group is tagged as willing / unwilling to share a table

#### 2.2.2 Queue & Table Management
- Table sharing is enabled
- When a table frees, the earliest-waiting suitable group across all matching queues is seated
- Groups are assigned the **smallest available table** that fits them (minimize waste)
- Queue boundaries are fixed for the duration of each simulation run
- Two queue sets maintained:
  - **Regular queue** — standard arrivals
  - **Special queue** — late-comers (added after attendance confirmed)
  - Serve ratio: **3 regular : 1 special** (when special queue is non-empty)

#### 2.2.3 Simulation Mechanics
- Event-driven: time advances to the next arrival or table-free event
- All times in integer minutes; simultaneous events resolved by arrival order
- Fully deterministic — no randomness given the same inputs

#### 2.2.4 Input Data
- Input files are hand-crafted
- Basic error handling covers missing, empty, or malformed files
- Scenarios are realistic but not sourced from real restaurant data

### 2.3 Justification of Key Assumptions
- **Walkaway behavior enabled** — trades simplicity for a more realistic model
- **Fixed dining duration** — ensures outcome differences are attributable solely to the configuration under test
- **Smallest suitable table assignment** — favors utilization efficiency; real-world deviations are discussed
- **Integer minute resolution** — sufficient for 1–3 hour scenarios; sub-minute precision adds complexity without meaningful benefit

---

## 3. Summary of Queue Management Approaches

### 3.1 Single Queue *(Classic Wait List)*
- **How it works:** Sign-up list, sequential seating, strictly first-come-first-served
- **Pros:** Simple to manage; perceived as fair
- **Cons:** Poor table yield; does not optimize turnover

### 3.2 Size-Based Queues *(Separate by Party Size)*
- **How it works:** Separate lists matched to table sizes
- **Pros:** Maximizes space efficiency; avoids table mismatch
- **Cons:** Can seat later-arriving large parties before earlier-arriving small parties — perceived unfairness

### 3.3 VIP Priority Queue *(Preemptive)*
- **How it works:** Main queue with host-discretion VIP skipping
- **Pros:** Rewards loyalty; social proof from high-profile guests
- **Cons:** Alienates regular customers; risks negative reviews and churn

### 3.4 Reservation-Based System
- **How it works:** Advance time-slot booking; walk-ins take remaining capacity
- **Pros:** Predictable staffing and prep; guaranteed seating for customers
- **Cons:** No-shows waste tables; late arrivals create idle seats while walk-ins wait

### 3.5 Hybrid Queue with Table-Type Matching
- **How it works:** Size-based sub-lists further split by table type (booth, high-top, patio, etc.)
- **Pros:** Maximizes guest comfort; eliminates last-second seating negotiations
- **Cons:** High cognitive load for hosts; collapses without dedicated software

### 3.6 Virtual Queue *(Buzzer / App-Based)*
- **How it works:** Remote queue via app/SMS; guests notified when table is ready
- **Pros:** Eliminates lobby congestion; perceived as modern and respectful of guests' time
- **Cons:** "Wanderer problem" — guests miss their window; functionally similar to reservation no-shows

### 3.7 Overbooking with Standby Buffer *(Airline Model)*
- **How it works:** Overbook reservations based on predicted no-show rates; standby walk-in list fills gaps
- **Pros:** Near-zero empty tables; forces useful no-show data tracking
- **Cons:** Catastrophic failure when no-shows don't materialize; no compensation mechanism like airlines

---

## 4. Timeline & Milestones

| Milestone | Description | Target Date | Responsible |
|---|---|---|---|
| Project Kick-off & Planning | Finalize roles, scope, assumptions, initial research plan | 18 Mar 2026 ✅ | All members |
| Research Completion | Queue strategy survey, comparison table, assumptions docs | 22 Mar 2026 ✅| Liu Haojie, Yan Weibo, Xu Jiahang |
| Data Model & File I/O Done | Customer/table/queue data structures and file loading | 23 Mar 2026 ✅| Liu Haojie, Gao Junhang, Xu Jiahang |
| Core Simulation Implemented | Event-driven logic for arrivals, seating, and time advance | 7 Apr 2026 | Liu Haojie, Gao Junhang, Xu Jiahang |
| Metrics & Output Completed | Wait times, utilization, queue lengths, service level | 9 Apr 2026 | Gao Junhang, Xu Jiahang |
| Scenario Design & Input Files | 5–6 paired scenarios, one factor varied each | 9 Apr 2026 | Gao Junhang, Zhou Bocheng |
| Evaluation & Analysis | Run simulations, compare metrics, write trade-off discussion | 12 Apr 2026 | All members |
| Video Demo Recording | Demo video showing simulation runs and key results | 19 Apr 2026 | Gao Junhang, Zhou Bocheng |
| Final Report Draft | Combine all sections (research, code, evaluation, etc.) | 19 Apr 2026 | Yan Weibo, Zhou Bocheng |
| Project Submission & Final Checks | Final polish, test everything, submit code/report/video | 26 Apr 2026 | All members |
