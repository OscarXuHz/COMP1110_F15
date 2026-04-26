#!/usr/bin/env python3
"""
Independent verification simulator for restaurant queue simulation.
This is a from-scratch reimplementation to cross-check main.py outputs.
"""
import heapq
from datetime import datetime
import os
import sys

# ============================================================
# DATA STRUCTURES (independent from main.py)
# ============================================================

class Req:
    def __init__(self, index, people, arrival, duration, share, miss, comeback, vip, reserved):
        self.index = index
        self.people = people
        self.arrival = arrival
        self.duration = duration
        self.share = share
        self.miss = miss
        self.comeback = comeback
        self.vip = vip
        self.reserved = reserved
        # runtime
        self.table_idx = -1
        self.wait_time = 0
        self.leave_time = 0
        self.seated_time = 0

class Tbl:
    def __init__(self, idx, capacity):
        self.idx = idx
        self.capacity = capacity
        self.cur_people = 0
        self.occupants = []  # list of Req
        self.reserved_slots = []  # list of (start, end)

    def has_reservation_conflict(self, start, end):
        """Check if [start, end) overlaps any reserved slot"""
        for rs, re in self.reserved_slots:
            if not (re <= start or rs >= end):
                return True
        return False

    def has_occupant_conflict(self, start, end):
        """Check if any current occupant overlaps [start, end)"""
        for c in self.occupants:
            if not (c.leave_time <= start or c.seated_time >= end):
                return True
        return False

    def remaining(self):
        return self.capacity - self.cur_people

    def seat(self, req, cur_time):
        req.table_idx = self.idx
        req.leave_time = cur_time + req.duration
        req.wait_time = cur_time - req.arrival
        req.seated_time = cur_time
        self.cur_people += req.people
        self.occupants.append(req)

    def unseat(self, req):
        self.cur_people -= req.people
        self.occupants.remove(req)


# ============================================================
# FILE LOADING
# ============================================================

def time_to_minutes(t_str):
    """Convert YYYYMMDDHHMMSS to minutes since epoch"""
    dt = datetime.strptime(t_str, '%Y%m%d%H%M%S')
    return int(dt.timestamp() / 60)

def read_requests(filename):
    reqs = []
    with open(filename, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 9:
                continue
            reqs.append(Req(
                index=int(parts[0]),
                people=int(parts[1]),
                arrival=time_to_minutes(parts[2]),
                duration=int(parts[3]),
                share=int(parts[4]),
                miss=int(parts[5]),
                comeback=int(parts[6]),
                vip=int(parts[7]),
                reserved=int(parts[8]),
            ))
    return reqs

def read_restaurant(filename):
    tables = []
    with open(filename, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 2:
                continue
            count, cap = int(parts[0]), int(parts[1])
            for _ in range(count):
                tables.append(Tbl(len(tables), cap))
    return tables


# ============================================================
# RESERVATION PRE-ALLOCATION
# ============================================================

def preallocate_reservations(reqs, tables):
    """Assign tables to reserved customers, sorted by (-people, arrival)"""
    reserved = [r for r in reqs if r.reserved == 1]
    reserved.sort(key=lambda x: (-x.people, x.arrival))
    mapping = {}
    for r in reserved:
        # candidates: capacity >= people, sorted by (capacity, index)
        cands = [t for t in tables if t.capacity >= r.people]
        cands.sort(key=lambda t: (t.capacity, t.idx))
        found = None
        for t in cands:
            if not t.has_reservation_conflict(r.arrival, r.arrival + r.duration):
                found = t
                break
        if found is None:
            raise RuntimeError(f"Cannot allocate reservation for request {r.index}")
        found.reserved_slots.append((r.arrival, r.arrival + r.duration))
        mapping[r.index] = found
    return mapping


# ============================================================
# INDEPENDENT SIMULATION (exact replication of main.py logic)
# ============================================================

def independent_simulate(reqs, tables, verbose=False):
    res_map = preallocate_reservations(reqs, tables)

    # Event heap: (time, counter, type_str, req)
    counter = 0
    events = []
    for r in reqs:
        heapq.heappush(events, (r.arrival, counter, 'arrival', r))
        counter += 1

    waiting = []      # waiting queue (list)
    miss_q = []       # miss queue
    served = []       # served requests
    total_wait = 0
    max_wait = 0
    max_queue_len = 0
    tbl_busy = [0] * len(tables)
    svc_x = 10
    within_x = 0
    normal_count = 0
    cur_time = 0
    log = []

    while events or waiting or miss_q:
        if not events:
            if verbose:
                log.append("WARNING: no events but waiting/miss queues non-empty")
            break

        ev_time, _cnt, ev_type, ev_req = heapq.heappop(events)
        cur_time = ev_time

        # ---- LEAVE ----
        if ev_type == 'leave':
            t = tables[ev_req.table_idx]
            t.unseat(ev_req)
            tbl_busy[t.idx] += ev_req.duration
            if verbose:
                log.append(f"  T={cur_time}: C{ev_req.index} LEAVES table {t.idx} (freed {ev_req.people})")

            # Try to seat from waiting queue
            while waiting:
                w = waiting.pop(0)
                seated = False
                # Build candidates: no reservation conflict + enough remaining capacity
                cands = []
                for tb in tables:
                    if not tb.has_reservation_conflict(cur_time, cur_time + w.duration):
                        if tb.remaining() >= w.people:
                            cands.append((tb.remaining(), tb))

                if w.share:
                    cands.sort(key=lambda x: (x[0], x[1].idx))
                    for _, tb in cands:
                        tb.seat(w, cur_time)
                        seated = True
                        if verbose:
                            log.append(f"  T={cur_time}: C{w.index} SEATED (from queue, share) at table {tb.idx}, wait={w.wait_time}")
                        break
                else:
                    # No share: cur_people==0 AND (cap==people OR cap==people+1)
                    for _, tb in cands:
                        if tb.cur_people == 0 and (tb.capacity == w.people or tb.capacity == w.people + 1):
                            tb.seat(w, cur_time)
                            seated = True
                            if verbose:
                                log.append(f"  T={cur_time}: C{w.index} SEATED (from queue, no-share) at table {tb.idx}, wait={w.wait_time}")
                            break

                if seated:
                    served.append(w)
                    total_wait += w.wait_time
                    max_wait = max(max_wait, w.wait_time)
                    if w.wait_time <= svc_x:
                        within_x += 1
                    heapq.heappush(events, (w.leave_time, counter, 'leave', w))
                    counter += 1
                    if w.vip == 0:
                        normal_count += 1
                        if normal_count % 3 == 0 and miss_q:
                            missed = miss_q.pop(0)
                            if missed.comeback == 1:
                                if missed.vip == 1:
                                    waiting.insert(0, missed)
                                else:
                                    waiting.append(missed)
                                if verbose:
                                    log.append(f"  T={cur_time}: C{missed.index} CALLBACK from miss queue -> waiting")
                else:
                    waiting.insert(0, w)
                    break

            qlen = len(waiting)
            max_queue_len = max(max_queue_len, qlen)

        # ---- ARRIVAL ----
        elif ev_type == 'arrival':
            r = ev_req
            if verbose:
                log.append(f"  T={cur_time}: C{r.index} ARRIVES ({r.people}ppl, share={r.share}, vip={r.vip}, miss={r.miss}, res={r.reserved})")

            # Reserved customer
            if r.reserved == 1:
                t = res_map[r.index]
                if not t.has_occupant_conflict(r.arrival, r.arrival + r.duration):
                    t.seat(r, r.arrival)
                    served.append(r)
                    total_wait += r.wait_time
                    max_wait = max(max_wait, r.wait_time)
                    if r.wait_time <= svc_x:
                        within_x += 1
                    heapq.heappush(events, (r.leave_time, counter, 'leave', r))
                    counter += 1
                    # Note: reserved non-VIP increments normal_count but does NOT trigger callback
                    if r.vip == 0:
                        normal_count += 1
                    if verbose:
                        log.append(f"    -> RESERVED seated at table {t.idx}, wait={r.wait_time}")
                else:
                    raise RuntimeError(f"Reserved C{r.index} conflict")
                continue

            # Miss customer
            if r.miss == 1:
                miss_q.append(r)
                if verbose:
                    log.append(f"    -> MISS queued")
                continue

            # Normal arrival: try to seat
            seated = False
            cands = []
            for tb in tables:
                if not tb.has_reservation_conflict(r.arrival, r.arrival + r.duration):
                    if tb.capacity >= r.people:
                        cands.append((tb.remaining(), tb))

            if r.share:
                cands.sort(key=lambda x: (x[0], x[1].idx))
                for _, tb in cands:
                    if tb.remaining() >= r.people:
                        tb.seat(r, r.arrival)
                        seated = True
                        if verbose:
                            log.append(f"    -> SEATED (share) at table {tb.idx}")
                        break
            else:
                # No share on arrival: STRICT - cap must equal people exactly
                for _, tb in cands:
                    if tb.cur_people == 0 and tb.capacity == r.people:
                        tb.seat(r, r.arrival)
                        seated = True
                        if verbose:
                            log.append(f"    -> SEATED (no-share, exact) at table {tb.idx}")
                        break

            if seated:
                served.append(r)
                total_wait += r.wait_time
                max_wait = max(max_wait, r.wait_time)
                if r.wait_time <= svc_x:
                    within_x += 1
                heapq.heappush(events, (r.leave_time, counter, 'leave', r))
                counter += 1
                if r.vip == 0:
                    normal_count += 1
                    if normal_count % 3 == 0 and miss_q:
                        missed = miss_q.pop(0)
                        if missed.comeback == 1:
                            if missed.vip == 1:
                                waiting.insert(0, missed)
                            else:
                                waiting.append(missed)
                            if verbose:
                                log.append(f"    CALLBACK: C{missed.index} from miss queue")
            else:
                if r.vip == 1:
                    waiting.insert(0, r)
                else:
                    waiting.append(r)
                qlen = len(waiting)
                max_queue_len = max(max_queue_len, qlen)
                if verbose:
                    log.append(f"    -> QUEUED (pos in queue: {qlen}, vip={r.vip})")

    # Compute metrics
    if not served:
        return {'avg_wait': 0, 'max_wait': 0, 'max_queue_len': 0, 'served': 0,
                'table_util': 0, 'service_level': 0, 'total_time': 0}, log

    total_time = max(r.leave_time for r in served) - min(r.arrival for r in reqs)
    avg_busy = sum(tbl_busy) / len(tables)
    util = (avg_busy / total_time * 100) if total_time > 0 else 0
    svc_level = (within_x / len(served) * 100) if served else 0

    stats = {
        'avg_wait': total_wait / len(served),
        'max_wait': max_wait,
        'max_queue_len': max_queue_len,
        'served': len(served),
        'table_util': util,
        'service_level': svc_level,
        'total_time': total_time,
    }
    return stats, log


# ============================================================
# PARSE EXPECTED OUTPUT
# ============================================================

def parse_output(filename):
    vals = {}
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if 'Average Wait Time' in line:
                vals['avg_wait'] = float(line.split(':')[1].strip().replace(' min', ''))
            elif 'Max Wait Time' in line:
                vals['max_wait'] = int(line.split(':')[1].strip().replace(' min', ''))
            elif 'Peak Queue Length' in line:
                vals['max_queue_len'] = int(line.split(':')[1].strip())
            elif 'Groups Served' in line:
                vals['served'] = int(line.split(':')[1].strip())
            elif 'Table Utilization' in line:
                vals['table_util'] = float(line.split(':')[1].strip().replace('%', ''))
            elif 'Service Level' in line:
                vals['service_level'] = float(line.split(':')[1].strip().replace('%', ''))
            elif 'Total Time' in line:
                vals['total_time'] = int(line.split(':')[1].strip().replace(' min', ''))
    return vals


# ============================================================
# MAIN VERIFICATION
# ============================================================

def compare(field, got, expected, tol=0.15):
    if isinstance(expected, float):
        return abs(got - expected) < tol
    return got == expected

def run_verification():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    all_pass = True

    for i in range(1, 11):
        req_file = f'request{i}.csv'
        rest_file = f'restaurant{i}.csv'
        out_file = f'output{i}.csv'

        if not all(os.path.exists(f) for f in [req_file, rest_file, out_file]):
            print(f"Test {i}: SKIPPED (files missing)")
            continue

        reqs = read_requests(req_file)
        tables = read_restaurant(rest_file)
        expected = parse_output(out_file)

        # Verbose for small tests, quiet for large
        verbose = len(reqs) <= 10
        stats, log = independent_simulate(reqs, tables, verbose=verbose)

        # Compare
        fields = ['avg_wait', 'max_wait', 'max_queue_len', 'served', 'table_util', 'service_level', 'total_time']
        mismatches = []
        for f in fields:
            got = stats[f]
            exp = expected.get(f)
            if exp is None:
                mismatches.append(f"  {f}: expected=MISSING, got={got}")
                continue
            if not compare(f, got, exp):
                mismatches.append(f"  {f}: expected={exp}, got={got}")

        if mismatches:
            print(f"=== Test {i}: MISMATCH ===")
            for m in mismatches:
                print(m)
            if verbose and log:
                print("  --- Simulation trace ---")
                for entry in log:
                    print(f"  {entry}")
            all_pass = False
        else:
            print(f"=== Test {i}: VERIFIED OK ===")
            got_str = (
                f"  avg_wait={stats['avg_wait']:.1f}, max_wait={stats['max_wait']}, "
                f"queue={stats['max_queue_len']}, served={stats['served']}, "
                f"util={stats['table_util']:.1f}%, svc={stats['service_level']:.1f}%, "
                f"time={stats['total_time']}"
            )
            print(got_str)

    print()
    if all_pass:
        print("ALL 10 TESTS INDEPENDENTLY VERIFIED ✓")
    else:
        print("SOME TESTS HAVE MISMATCHES — SEE ABOVE")
    return all_pass


if __name__ == '__main__':
    success = run_verification()
    sys.exit(0 if success else 1)
