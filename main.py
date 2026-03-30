import heapq
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple, Optional

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

@dataclass
class Table:
    index: int
    max_people: int
    cur_people: int = 0
    customers: List[Request] = field(default_factory=list)
    # 预留占用区间列表 (start, end)
    reserved_slots: List[Tuple[int, int]] = field(default_factory=list)

    def is_free(self, start: int, end: int) -> bool:
        """检查在 [start, end) 时间段内是否完全空闲（无顾客占用且无预留）"""
        # 检查当前顾客
        for c in self.customers:
            if not (c.leave_time <= start or c.arrival >= end):
                return False
        # 检查预留
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
        self.customers.append(req)

    def free(self, req: Request):
        self.cur_people -= req.people
        self.customers.remove(req)

# ---------- 辅助函数 ----------
def parse_time(t_str: str) -> int:
    """将 YYYYMMDDHHMMSS 转换为从第一个顾客到达开始的分钟数"""
    dt = datetime.strptime(t_str, '%Y%m%d%H%M%S')
    return int(dt.timestamp() / 60)

def load_requests(filename: str) -> List[Request]:
    """Load requests from CSV file"""
    requests = []
    with open(filename, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 9:
                continue
            idx, peo, arr, dur, share, miss, comeback, vip, res = parts
            req = Request(
                index=int(idx),
                people=int(peo),
                arrival=parse_time(arr),
                duration=int(dur),
                share=int(share),
                miss=int(miss),
                comeback=int(comeback),
                vip=int(vip),
                reserved=int(res)
            )
            requests.append(req)
    return requests

def allocate_reserved_tables(requests: List[Request], tables: List[Table]):
    """
    为预订顾客提前分配桌子（避免冲突）
    返回预订顾客的 (request.index, table) 映射，并在桌子中记录预留区间
    """
    # 按人数从大到小分配，减少冲突
    reserved_reqs = [r for r in requests if r.reserved == 1]
    reserved_reqs.sort(key=lambda x: (-x.people, x.arrival))
    assigned = {}
    for req in reserved_reqs:
        # 预订顾客必须预留整桌：选择能容纳该人数的最小桌子
        candidates = [t for t in tables if t.max_people >= req.people]
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
            raise RuntimeError(f"无法为预订顾客 {req.index} 分配桌子，请检查数据")
        # 记录预留区间
        chosen.reserved_slots.append((req.arrival, req.arrival + req.duration))
        assigned[req.index] = chosen
    return assigned

# ---------- 模拟主函数 ----------
def simulate(requests: List[Request], tables: List[Table]) -> dict:
    # 为预订顾客预留桌子
    reserved_map = allocate_reserved_tables(requests, tables)

    # 事件队列: (时间, 计数器, 类型, 请求)
    event_counter = 0
    event_queue = []
    for req in requests:
        heapq.heappush(event_queue, (req.arrival, event_counter, 'arrival', req))
        event_counter += 1

    # 等待队列: VIP 在队首，普通顾客在队尾
    waiting_queue = []
    # 过号队列
    miss_queue = []   # 元素为 Request

    # 统计变量
    served_requests = []
    total_wait = 0
    max_wait = 0
    queue_lengths = []          # 记录等待队列长度变化
    max_queue_length = 0
    # 桌子利用率: 记录每张桌子的累计占用时间
    table_busy_time = [0] * len(tables)
    # 服务等级: 假设 X = 10 分钟
    service_level_X = 10
    served_within_X = 0

    # 计数器: 每分配3个普通顾客，处理一个过号
    normal_served_count = 0

    # 模拟循环
    cur_time = 0
    last_event_time = requests[0].arrival if requests else 0

    while event_queue or waiting_queue or miss_queue:
        # 如果没有未来事件但有等待队列，则时间不能前进，但等待队列中的顾客只能由离开事件触发分配
        # 因此需要检查是否有离开事件即将发生
        if not event_queue:
            # 没有事件，但等待队列非空，说明所有人都卡住了（桌子满且无人离开）——实际上不可能，因为总有离开事件
            # 但为了安全，跳出
            break

        # 取出下一个事件
        ev_time, _, ev_type, ev_req = heapq.heappop(event_queue)
        cur_time = ev_time

        # ---------- 离开事件 ----------
        if ev_type == 'leave':
            t = ev_req.table
            t.free(ev_req)
            # 更新桌子占用时间
            table_busy_time[t.index] += ev_req.duration

            # 尝试从等待队列中分配
            while waiting_queue:
                w_req = waiting_queue.pop(0)
                # 重新尝试分配
                assigned = False
                # 根据拼桌意愿选择合适桌子
                candidates = []
                for t in tables:
                    if t.is_free(cur_time, cur_time + w_req.duration):
                        if t.max_people >= w_req.people:
                            candidates.append((t.max_people - t.cur_people, t))
                # 愿意拼桌则找剩余空间最小的，否则找完全空闲且人数匹配的
                if w_req.share:
                    candidates.sort(key=lambda x: (x[0], x[1].index))
                    for _, t in candidates:
                        if t.max_people - t.cur_people >= w_req.people:
                            t.seat(w_req, cur_time)
                            assigned = True
                            break
                else:
                    # 不愿拼桌：必须整桌空且人数匹配
                    for _, t in candidates:
                        if t.cur_people == 0 and t.max_people == w_req.people:
                            t.seat(w_req, cur_time)
                            assigned = True
                            break
                if assigned:
                    served_requests.append(w_req)
                    total_wait += w_req.wait_time
                    max_wait = max(max_wait, w_req.wait_time)
                    if w_req.wait_time <= service_level_X:
                        served_within_X += 1
                    # 插入离开事件
                    heapq.heappush(event_queue, (w_req.leave_time, event_counter, 'leave', w_req))
                    event_counter += 1
                    # 计数器：如果是普通顾客（非VIP），增加
                    if w_req.vip == 0:
                        normal_served_count += 1
                        # 每3个普通顾客处理一个过号
                        if normal_served_count % 3 == 0 and miss_queue:
                            missed_req = miss_queue.pop(0)
                            if missed_req.comeback == 1:
                                # 重新加入等待队列（VIP 插队首，普通加队尾）
                                if missed_req.vip == 1:
                                    waiting_queue.insert(0, missed_req)
                                else:
                                    waiting_queue.append(missed_req)
                else:
                    # 分配失败，放回等待队列队首（防止死循环）
                    waiting_queue.insert(0, w_req)
                    break   # 无法继续分配，跳出
            # 记录等待队列长度
            queue_lengths.append(len(waiting_queue))
            max_queue_length = max(max_queue_length, len(waiting_queue))

        # ---------- 到达事件 ----------
        elif ev_type == 'arrival':
            req = ev_req
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
                    heapq.heappush(event_queue, (req.leave_time, event_counter, 'leave', req))
                    event_counter += 1
                    if req.vip == 0:
                        normal_served_count += 1
                else:
                    # 理论上不会发生，因为预留已保证
                    raise RuntimeError(f"预订顾客 {req.index} 预留冲突")
                continue

            # 普通顾客处理过号标记
            if req.miss == 1:
                # 过号顾客先进入过号队列，稍后回叫
                miss_queue.append(req)
                continue

            # 尝试分配
            assigned = False
            # 先按VIP插队？其实到达时直接尝试分配，不需要等待队列插队
            candidates = []
            for t in tables:
                if t.is_free(req.arrival, req.arrival + req.duration):
                    if t.max_people >= req.people:
                        candidates.append((t.max_people - t.cur_people, t))
            if req.share:
                candidates.sort(key=lambda x: (x[0], x[1].index))
                for _, t in candidates:
                    if t.max_people - t.cur_people >= req.people:
                        t.seat(req, req.arrival)
                        assigned = True
                        break
            else:
                for _, t in candidates:
                    if t.cur_people == 0 and t.max_people == req.people:
                        t.seat(req, req.arrival)
                        assigned = True
                        break

            if assigned:
                served_requests.append(req)
                total_wait += req.wait_time
                max_wait = max(max_wait, req.wait_time)
                if req.wait_time <= service_level_X:
                    served_within_X += 1
                heapq.heappush(event_queue, (req.leave_time, event_counter, 'leave', req))
                event_counter += 1
                if req.vip == 0:
                    normal_served_count += 1
                    if normal_served_count % 3 == 0 and miss_queue:
                        missed_req = miss_queue.pop(0)
                        if missed_req.comeback == 1:
                            # 重新加入等待队列（VIP 插队首，普通加队尾）
                            if missed_req.vip == 1:
                                waiting_queue.insert(0, missed_req)
                            else:
                                waiting_queue.append(missed_req)
            else:
                # 无法分配，进入等待队列（VIP 插队首，普通加队尾）
                if req.vip == 1:
                    waiting_queue.insert(0, req)
                else:
                    waiting_queue.append(req)
                # 记录等待队列长度
                queue_lengths.append(len(waiting_queue))
                max_queue_length = max(max_queue_length, len(waiting_queue))

    # 计算总模拟时长：最后一个顾客离开时间
    total_time = max((r.leave_time for r in served_requests), default=0) - min((r.arrival for r in requests), default=0)

    # 桌子利用率
    total_table_time = sum(table_busy_time) / len(tables)  # 平均占用时间
    simulation_duration = total_time
    table_utilization = (total_table_time / simulation_duration) * 100 if simulation_duration > 0 else 0

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

# ---------- 主函数 ----------
def main():
    requests = load_requests('requests.csv')

    # 餐桌配置
    table_config = [(5,2), (3,4), (2,6), (1,8)]  # (数量, 容量)
    tables = []
    for count, cap in table_config:
        for _ in range(count):
            tables.append(Table(len(tables), cap))

    # 模拟
    stats = simulate(requests, tables)

    print("Simulation Result:")
    print("------------------")
    print(f"Average Wait Time: {stats['avg_wait']:.1f} min")
    print(f"Max Wait Time: {stats['max_wait']} min")
    print(f"Peak Queue Length: {stats['max_queue_len']}")
    print(f"Groups Served: {stats['served']}")
    print(f"Table Utilization: {stats['table_util']:.1f}%")
    print(f"Service Level (seated within 10 min): {stats['service_level']:.1f}%")
    print(f"Total Time: {stats['total_time']} min")

if __name__ == "__main__":
    main()
