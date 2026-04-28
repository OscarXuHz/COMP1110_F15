"""Restaurant Queue Simulator — core simulation engine.

Public API (imported by app.py and used by the CLI):
    Request, Table      — data model dataclasses
    parse_time          — YYYYMMDDHHMMSS → integer minutes
    load_requests       — read customer CSV file
    load_restaurant     — read table-config CSV file
    allocate_reserved_tables — pre-assign reserved tables
    allocate            — seat one waiting customer
    simulate            — run full event-driven simulation
"""
from __future__ import annotations

import heapq
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple, Optional

__all__ = [
    "Request",
    "Table",
    "parse_time",
    "load_requests",
    "load_restaurant",
    "allocate_reserved_tables",
    "allocate",
    "simulate",
]

# ---------- 数据类 ----------
@dataclass
class Request:
    index: int
    people: int
    arrival: int          # 相对时间（分钟）
    duration: int
    share: int            # 1=愿意拼桌
    miss: int             # 1=过号
    comeback: int         # 过号后是否返回
    vip: int              # 1=VIP
    reserved: int         # 1=预订
    # 运行时字段
    table: Optional['Table'] = None
    wait_time: int = 0
    leave_time: int = 0
    is_miss_reactivated: bool = False  # 标记是否已从过号队列激活（用于避免重复计数）

@dataclass
class Table:
    index: int
    max_people: int
    cur_people: int = 0
    customers: List[Request] = field(default_factory=list)   # 当前在座的顾客
    history: List[Request] = field(default_factory=list)     # 所有服务过的顾客（用于统计）
    # 预留占用区间列表 (start, end)
    reserved_slots: List[Tuple[int, int]] = field(default_factory=list)
    noshare: bool = False  # 是否禁止拼桌（v1.5.0 update）

    def is_free(self, start: int, end: int) -> bool:
        """检查在 [start, end) 时间段内是否与预留冲突（不检查顾客占用）"""
        # Oscar v1.4.1 update 这边只考虑预留冲突问题
        for rs, re in self.reserved_slots:
            if not (re <= start or rs >= end):
                return False
        return True
    
    def is_free_ignore_reserved(self, start: int, end: int) -> bool:
        """检查在 [start, end) 时间段内是否无顾客占用（忽略预留检查）"""
        for c in self.customers:
            if not (c.leave_time <= start or c.arrival >= end):
                return False
        return True

    def seat(self, req: Request, cur_time: int):
        req.table = self
        req.leave_time = cur_time + req.duration
        req.wait_time = cur_time - req.arrival
        self.cur_people += req.people
        #update v1.5.0
        if self.noshare:
            self.cur_people = self.max_people  # 如果禁止拼桌，直接占满
        self.customers.append(req)
        self.history.append(req)   # 记录历史用于最终统计

    def free(self, req: Request):
        self.cur_people -= req.people
        self.customers.remove(req)
        if self.noshare:
            self.noshare = False  # 释放后恢复拼桌能力
            self.cur_people = 0  # 直接清空人数
        # 注意：history 中的顾客不移除，用于统计

# ---------- 辅助函数 ----------
def parse_time(t_str: str) -> int:
    """将 YYYYMMDDHHMMSS 转换为分钟数"""
    dt = datetime.strptime(t_str, '%Y%m%d%H%M%S')
    return int(dt.timestamp() / 60)

def load_requests(filename: str) -> List[Request]:
    """Load requests from CSV file (9 columns, no header)."""
    requests = []
    with open(filename, 'r', encoding='utf-8') as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(',')
            if len(parts) < 9:
                print(f"  [warning] line {lineno} skipped (expected 9 columns, got {len(parts)})")
                continue
            try:
                idx, peo, arr, dur, share, miss, comeback, vip, res = parts[:9]
                req = Request(
                    index=int(idx),
                    people=int(peo),
                    arrival=parse_time(arr.strip()),
                    duration=int(dur),
                    share=int(share),
                    miss=int(miss),
                    comeback=int(comeback),
                    vip=int(vip),
                    reserved=int(res)
                )
                requests.append(req)
            except (ValueError, Exception) as e:
                print(f"  [warning] line {lineno} skipped ({e})")
    return requests


def load_restaurant(filename: str) -> List[Table]:
    """Load table configuration from CSV file (2 columns: count,capacity, no header)."""
    tables: List[Table] = []
    with open(filename, 'r', encoding='utf-8') as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split(',')
            if len(parts) < 2:
                print(f"  [warning] line {lineno} skipped (expected 2 columns, got {len(parts)})")
                continue
            try:
                count, capacity = int(parts[0]), int(parts[1])
                if count <= 0 or capacity <= 0:
                    print(f"  [warning] line {lineno} skipped (count and capacity must be >= 1)")
                    continue
                for _ in range(count):
                    tables.append(Table(len(tables), capacity))
            except ValueError as e:
                print(f"  [warning] line {lineno} skipped ({e})")
    return tables

def allocate_reserved_tables(requests: List[Request], tables: List[Table]) -> dict:
    """
    为预订顾客提前分配桌子（避免冲突）
    返回预订顾客的 (request.index, table) 映射，并在桌子中记录预留区间
    v1.1 修改：无法分配时抛出异常，确保返回字典类型
    """
    # 按人数从大到小分配，减少冲突
    reserved_reqs = [r for r in requests if r.reserved == 1]
    reserved_reqs.sort(key=lambda x: (-x.people, x.arrival))
    assigned = {}
    for req in reserved_reqs:
        # 预订顾客必须预留整桌：选择能容纳该人数的最小桌子
        candidates = [t for t in tables if t.max_people >= req.people]
        # v5.1.2 update NULL pretection -> 改为异常
        if not candidates:
            raise RuntimeError(f"Cannot allocate table for reserved request {req.index}: no table large enough")
        candidates.sort(key=lambda t: (t.max_people, t.index))  # 按容量从小到大排序
        chosen = None
        for t in candidates:
            # 检查该时间段内是否已有预留冲突
            conflict = False
            for rs, re in t.reserved_slots:
                if not (re <= req.arrival or rs >= req.arrival + req.duration):
                    conflict = True
                    break
            if not conflict:
                chosen = t
                break
        if chosen is None:
            raise RuntimeError(f"Cannot allocate table for request {req.index} due to reservation conflict")
        # 记录预留区间
        chosen.reserved_slots.append((req.arrival, req.arrival + req.duration))
        assigned[req.index] = chosen
    return assigned

# update v4.1.2 整合分配逻辑，避免重复代码
def allocate(tables: List[Table], w_req: Request, cur_time: int) -> bool:
    assigned = False
    # 根据拼桌意愿选择合适桌子
    candidates = []
    for t in tables:
        if t.is_free(cur_time, cur_time + w_req.duration):
            # v1.4.1 update update 保证无reservation 冲突，只需保证当前有足够空位，即可完成落座
            if t.max_people - t.cur_people >= w_req.people:
                candidates.append((t.max_people - t.cur_people, t))
    # 愿意拼桌则找剩余空间最小的，否则找完全空闲且人数匹配的
    if w_req.share:
        candidates.sort(key=lambda x: (x[0], x[1].index))
        for _, t in candidates:
            t.seat(w_req, cur_time)
            assigned = True
            break
    else:
        # update 1.4.2 重写 noshare 逻辑
        # 不愿拼桌：找到最小的完全空闲且人数够的桌子
        candidates = [(s, t) for s, t in candidates if t.cur_people == 0 and t.max_people >= w_req.people]
        if not candidates:
            return False
        candidates.sort(key=lambda x: (x[0], x[1].index))
        candidates[0][1].noshare = True
        candidates[0][1].seat(w_req, cur_time)
        assigned = True
    return assigned

# ---------- 模拟主函数 ----------
def simulate(requests: List[Request], tables: List[Table]) -> dict:
    if not requests:
        raise ValueError("requests list must not be empty")
    if not tables:
        raise ValueError("tables list must not be empty")
    # 为预订顾客预留桌子
    reserved_map = allocate_reserved_tables(requests, tables)

    # 事件队列: (时间, 计数器, 类型, 请求)
    event_count = 0
    event_queue = []
    for req in requests:
        heapq.heappush(event_queue, (req.arrival, event_count, 'arrival', req))
        event_count += 1

    # 等待队列: 使用稳定排序 (VIP优先, 同VIP按到达时间, 再按唯一ID)
    waiting_queue = []          # 元素为 (-vip, arrival, queue_id, req)
    queue_id_counter = 0        # 全局唯一ID保证稳定顺序

    # 过号队列: 存放已经 comeback 但尚未被激活的顾客
    miss_queue: deque = deque()  # 元素为 Request（使用 deque 保证 popleft 为 O(1)）

    # 统计变量
    served_requests = []
    total_wait = 0
    max_wait = 0
    queue_lengths = []          # 记录等待队列长度变化
    max_queue_length = 0
    # 服务等级: 假设 X = 10 分钟
    service_level_X = 10
    served_within_X = 0

    # 过号激活计数器: 每服务3个普通顾客，激活一个过号顾客（激活后清零）
    normal_served_count = 0

    # 模拟开始和结束时间
    sim_start = min(req.arrival for req in requests) if requests else 0
    sim_end = 0

    # 辅助函数：尝试从等待队列分配顾客（遍历整个队列，尽可能多分配）
    def try_allocate_from_waiting(cur_time):
        nonlocal normal_served_count, served_requests, total_wait, max_wait, served_within_X, event_count, sim_end, queue_id_counter
        allocated_any = True
        while allocated_any and waiting_queue:
            allocated_any = False
            new_waiting = []  # 暂存本轮未分配的顾客
            while waiting_queue:
                neg_vip, arr, qid, w_req = heapq.heappop(waiting_queue)
                if allocate(tables, w_req, cur_time):
                    # 分配成功
                    served_requests.append(w_req)
                    total_wait += w_req.wait_time
                    max_wait = max(max_wait, w_req.wait_time)
                    if w_req.wait_time <= service_level_X:
                        served_within_X += 1
                    heapq.heappush(event_queue, (w_req.leave_time, event_count, 'leave', w_req))
                    event_count += 1
                    sim_end = max(sim_end, w_req.leave_time)
                    allocated_any = True

                    # 如果是普通顾客（非VIP、非预订、非已激活过号），增加计数并可能激活过号顾客
                    if w_req.vip == 0 and w_req.reserved == 0 and not w_req.is_miss_reactivated:
                        normal_served_count += 1
                        # 每累计3个普通顾客，激活一个过号顾客，然后计数器清零
                        if normal_served_count >= 3 and miss_queue:
                            missed_req = miss_queue.popleft()
                            missed_req.arrival = cur_time
                            missed_req.is_miss_reactivated = True
                            queue_id_counter += 1
                            heapq.heappush(waiting_queue, (-missed_req.vip, missed_req.arrival, queue_id_counter, missed_req))
                            normal_served_count = 0

                    # 将本轮暂存但未分配的顾客放回队列
                    for item in new_waiting:
                        heapq.heappush(waiting_queue, item)
                    new_waiting.clear()
                    break  # 桌子状态已变，重新从头开始尝试
                else:
                    # 分配失败，暂存后继续尝试下一个
                    new_waiting.append((neg_vip, arr, qid, w_req))
            # 内层结束后，将所有未分配的顾客放回队列
            for item in new_waiting:
                heapq.heappush(waiting_queue, item)

        # 如果等待队列为空且过号队列非空，则一次性激活所有过号顾客
        if not waiting_queue and miss_queue:
            for missed_req in miss_queue:
                missed_req.arrival = cur_time
                missed_req.is_miss_reactivated = True
                queue_id_counter += 1
                heapq.heappush(waiting_queue, (-missed_req.vip, missed_req.arrival, queue_id_counter, missed_req))
            miss_queue.clear()
            normal_served_count = 0
            # 激活后可能还有空桌，继续尝试分配
            try_allocate_from_waiting(cur_time)

    # 模拟循环
    cur_time = 0
    while event_queue or waiting_queue or miss_queue:
        if not event_queue:
            # 没有未来事件但有等待或过号队列，则无法处理（没有离开事件释放桌子）
            print("Warning: No future events but non-empty queues. Exiting simulation.")
            break

        # 取出下一个事件
        ev_time, _, ev_type, ev_req = heapq.heappop(event_queue)
        cur_time = ev_time

        # ---------- 离开事件 ----------
        if ev_type == 'leave':
            t = ev_req.table
            t.free(ev_req)
            # 尝试从等待队列分配
            try_allocate_from_waiting(cur_time)
            # 记录等待队列长度
            queue_lengths.append(len(waiting_queue))
            max_queue_length = max(max_queue_length, len(waiting_queue))

        # ---------- 到达事件 ----------
        elif ev_type == 'arrival':
            req = ev_req

            # 过号且可返回的顾客：安排15分钟后返回（comeback事件）
            if req.miss == 1 and req.comeback == 1:
                comeback_time = req.arrival + 15
                heapq.heappush(event_queue, (comeback_time, event_count, 'comeback', req))
                event_count += 1
                continue

            # 过号且不返回的顾客：直接丢弃
            if req.miss == 1 and req.comeback == 0:
                continue

            # 预订顾客：直接使用预留的桌子
            if req.reserved == 1:
                t = reserved_map[req.index]
                # 检查预留是否仍然有效（没有其他顾客占用该时间段）
                if t.is_free_ignore_reserved(req.arrival, req.arrival + req.duration):
                    t.seat(req, req.arrival)
                    served_requests.append(req)
                    total_wait += req.wait_time
                    max_wait = max(max_wait, req.wait_time)
                    if req.wait_time <= service_level_X:
                        served_within_X += 1
                    heapq.heappush(event_queue, (req.leave_time, event_count, 'leave', req))
                    event_count += 1
                    sim_end = max(sim_end, req.leave_time)
                    # 预订顾客不是普通顾客，不影响 normal_served_count
                else:
                    raise RuntimeError(f"预订顾客 {req.index} 预留冲突")
                continue

            # 非预订、非过号的普通顾客或VIP
            if allocate(tables, req, req.arrival):
                served_requests.append(req)
                total_wait += req.wait_time
                max_wait = max(max_wait, req.wait_time)
                if req.wait_time <= service_level_X:
                    served_within_X += 1
                heapq.heappush(event_queue, (req.leave_time, event_count, 'leave', req))
                event_count += 1
                sim_end = max(sim_end, req.leave_time)
                # 普通顾客（非VIP）计数
                if req.vip == 0:
                    normal_served_count += 1
                    # 每累计3个普通顾客，激活一个过号顾客，然后清零
                    if normal_served_count >= 3 and miss_queue:
                        missed_req = miss_queue.popleft()
                        missed_req.arrival = cur_time
                        missed_req.is_miss_reactivated = True
                        queue_id_counter += 1
                        heapq.heappush(waiting_queue, (-missed_req.vip, missed_req.arrival, queue_id_counter, missed_req))
                        normal_served_count = 0
                # 如果等待队列非空，尝试分配（可能包含刚激活的过号顾客）
                if waiting_queue:
                    try_allocate_from_waiting(cur_time)
            else:
                # 无法立即服务，加入等待队列
                queue_id_counter += 1
                heapq.heappush(waiting_queue, (-req.vip, req.arrival, queue_id_counter, req))
                queue_lengths.append(len(waiting_queue))
                max_queue_length = max(max_queue_length, len(waiting_queue))

        # ---------- comeback 事件（过号顾客15分钟后返回）----------
        elif ev_type == 'comeback':
            req = ev_req
            # 顾客回来了，放入过号队列（等待被激活）
            miss_queue.append(req)
            # 注意：此时不分配，等待普通顾客服务触发激活或队列空时批量激活
            # 但可以检查一下如果当前没有等待队列，可能会立即激活
            if not waiting_queue:
                try_allocate_from_waiting(cur_time)
            continue

        # 每次事件后，如果等待队列非空，尝试分配（尤其是到达事件可能没有触发分配）
        if waiting_queue:
            try_allocate_from_waiting(cur_time)

    # 计算总模拟时长：第一个到达时间到最后一个离开时间
    total_time = sim_end - sim_start

    # 计算桌子利用率（基于历史记录合并区间）
    def calc_table_utilization(tables, sim_start, sim_end):
        total_busy = 0
        for t in tables:
            if not t.history:
                continue
            intervals = [(c.arrival, c.leave_time) for c in t.history]
            intervals.sort()
            merged = []
            for start, end in intervals:
                if not merged or start > merged[-1][1]:
                    merged.append([start, end])
                else:
                    merged[-1][1] = max(merged[-1][1], end)
            total_busy += sum(end - start for start, end in merged)
        sim_duration = sim_end - sim_start
        if sim_duration <= 0:
            return 0.0
        return (total_busy / (len(tables) * sim_duration)) * 100

    table_utilization = calc_table_utilization(tables, sim_start, sim_end)

    # 服务等级：X=10分钟
    service_level = (served_within_X / len(served_requests)) * 100 if served_requests else 0

    return {
        'avg_wait': total_wait / len(served_requests) if served_requests else 0,
        'max_wait': max_wait,
        'max_queue_len': max_queue_length,
        'served': len(served_requests),
        'table_util': table_utilization,
        'service_level': service_level,
        'total_time': total_time
    }

# ---------- CLI helpers ----------
def _print_results(stats: dict) -> None:
    print("\nSimulation Result:")
    print("------------------")
    print(f"Average Wait Time:                   {stats['avg_wait']:.1f} min")
    print(f"Max Wait Time:                       {stats['max_wait']} min")
    print(f"Peak Queue Length:                   {stats['max_queue_len']}")
    print(f"Groups Served:                       {stats['served']}")
    print(f"Table Utilization:                   {stats['table_util']:.1f}%")
    print(f"Service Level (seated within 10 min): {stats['service_level']:.1f}%")
    print(f"Total Time:                          {stats['total_time']} min")


def _ask_file(prompt: str, default: str) -> str:
    """Prompt for a filename, using default if the user just hits Enter."""
    raw = input(f"{prompt} [{default}]: ").strip()
    return raw if raw else default


# ---------- 主函数 ----------
def main():
    # current simulation state
    requests: List[Request] = []
    tables: List[Table] = []
    last_stats: dict = {}

    MENU = """
============================================
  Restaurant Queue Simulator — Main Menu
============================================
  1. Load restaurant settings (tables)
  2. Load customer requests
  3. Run simulation
  4. Show last results
  5. Export last results to file
  6. Exit
--------------------------------------------"""

    while True:
        print(MENU)
        choice = input("Enter option (1-6): ").strip()

        # ── 1. Load restaurant settings ──────────────────────────────────────
        if choice == '1':
            filename = _ask_file("Restaurant CSV file", "restaurant.csv")
            try:
                tables = load_restaurant(filename)
                if tables:
                    print(f"  Loaded {len(tables)} tables from '{filename}'.")
                    capacities: dict = {}
                    for t in tables:
                        capacities[t.max_people] = capacities.get(t.max_people, 0) + 1
                    for cap, cnt in sorted(capacities.items()):
                        print(f"    {cnt} x {cap}-seat table(s)")
                else:
                    print("  [error] No valid table entries found in file.")
            except FileNotFoundError:
                print(f"  [error] File not found: '{filename}'")
            except Exception as e:
                print(f"  [error] {e}")

        # ── 2. Load customer requests ─────────────────────────────────────────
        elif choice == '2':
            filename = _ask_file("Requests CSV file", "requests.csv")
            try:
                requests = load_requests(filename)
                if requests:
                    print(f"  Loaded {len(requests)} customer request(s) from '{filename}'.")
                    vip_count = sum(1 for r in requests if r.vip)
                    res_count = sum(1 for r in requests if r.reserved)
                    miss_count = sum(1 for r in requests if r.miss)
                    if vip_count:
                        print(f"    VIP customers: {vip_count}")
                    if res_count:
                        print(f"    Reserved customers: {res_count}")
                    if miss_count:
                        print(f"    Miss/comeback customers: {miss_count}")
                else:
                    print("  [error] No valid request entries found in file.")
            except FileNotFoundError:
                print(f"  [error] File not found: '{filename}'")
            except Exception as e:
                print(f"  [error] {e}")

        # ── 3. Run simulation ─────────────────────────────────────────────────
        elif choice == '3':
            if not tables:
                print("  [error] No tables loaded. Please choose option 1 first.")
                continue
            if not requests:
                print("  [error] No requests loaded. Please choose option 2 first.")
                continue
            try:
                import copy
                last_stats = simulate(copy.deepcopy(requests), copy.deepcopy(tables))
                _print_results(last_stats)
            except ValueError as e:
                print(f"  [error] {e}")
            except RuntimeError as e:
                print(f"  [error] Reservation conflict: {e}")
            except Exception as e:
                print(f"  [error] Unexpected error: {e}")

        # ── 4. Show last results ──────────────────────────────────────────────
        elif choice == '4':
            if last_stats:
                _print_results(last_stats)
            else:
                print("  No simulation has been run yet. Choose option 3 first.")

        # ── 5. Export results to file ─────────────────────────────────────────
        elif choice == '5':
            if not last_stats:
                print("  No results to export. Run a simulation first (option 3).")
                continue
            filename = _ask_file("Output file", "output.csv")
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("Simulation Result:\n")
                    f.write("------------------\n")
                    f.write(f"Average Wait Time: {last_stats['avg_wait']:.1f} min\n")
                    f.write(f"Max Wait Time: {last_stats['max_wait']} min\n")
                    f.write(f"Peak Queue Length: {last_stats['max_queue_len']}\n")
                    f.write(f"Groups Served: {last_stats['served']}\n")
                    f.write(f"Table Utilization: {last_stats['table_util']:.1f}%\n")
                    f.write(f"Service Level (seated within 10 min): {last_stats['service_level']:.1f}%\n")
                    f.write(f"Total Time: {last_stats['total_time']} min\n")
                print(f"  Results exported to '{filename}'.")
            except Exception as e:
                print(f"  [error] Could not write file: {e}")

        # ── 6. Exit ───────────────────────────────────────────────────────────
        elif choice == '6':
            print("Goodbye.")
            break

        else:
            print("  Invalid option. Please enter a number from 1 to 6.")


if __name__ == "__main__":
    main()
