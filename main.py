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
    noshare: bool = False  # 是否禁止拼桌（v1.5.0 update）

    def is_free(self, start: int, end: int) -> bool:
        """检查在 [start, end) 时间段内是否完全空闲（无顾客占用且无预留）"""
        # 检查当前顾客
        # for c in self.customers:
        #     if not (c.leave_time <= start or c.arrival >= end):
        #         return False
        # 检查预留

        #Oscar v1.4.1 update 这边只考虑预留冲突问题
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

    def free(self, req: Request):
        self.cur_people -= req.people
        self.customers.remove(req)
        if self.noshare:
            self.noshare = False  # 释放后恢复拼桌能力
            self.cur_people = 0  # 直接清空人数

# ---------- 辅助函数 ----------
def parse_time(t_str: str) -> int:
    """将 YYYYMMDDHHMMSS 转换为分钟数"""
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
            raise RuntimeError(f"Cannot allocate table for request {req.index}, please check the data")
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
        candidates.sort(key=lambda x: (x[0], x[1].index))
        # 现在的 candidates 只包含合适的桌子且按大小升序排序
        # 所以直接选第一个
        candidates[0][1].noshare = True
        candidates[0][1].seat(w_req, cur_time)
        assigned = True
    return assigned

#update v1.5.0 整合分配后续逻辑，避免重复代码
def assign(served_requests: List[Request], waiting_queue: List[Request], miss_queue: List[Request], event_queue: List[Tuple[int, int, str, Request]], event_count: int, tables: List[Table], service_level_X: int, served_within_X: int, total_wait: int, max_wait: int, normal_served_count: int, req: Request):
    served_requests.append(req)
    total_wait += req.wait_time
    max_wait = max(max_wait, req.wait_time)
    if req.wait_time <= service_level_X:
        served_within_X += 1
    # 插入离开事件
    heapq.heappush(event_queue, (req.leave_time, event_count, 'leave', req))
    event_count += 1
    # update v1.5.0 非 vip 也增加计数
    normal_served_count += 1
    # update v1.5.0 重写过号逻辑，使用优先队列维护 waitingqueue，过号不再考虑vip
    if normal_served_count % 3 == 0 and miss_queue:
        missed_req = miss_queue.pop(0)
        heapq.heappush(waiting_queue, (missed_req.vip, missed_req.arrival, missed_req)) 
        normal_served_count %= 3

# ---------- 模拟主函数 ----------
def simulate(requests: List[Request], tables: List[Table]) -> dict:
    # 为预订顾客预留桌子
    reserved_map = allocate_reserved_tables(requests, tables)

    # 事件队列: (时间, 计数器, 类型, 请求)
    # update v1.5.0 把 event_counter 改成 event_count，好听一点
    event_count = 0
    event_queue = []
    for req in requests:
        heapq.heappush(event_queue, (req.arrival, event_count, 'arrival', req))
        event_count += 1

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
            print("Warning: No future events but waiting queue is not empty. Exiting simulation.")
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
                w_req = heapq.heappop(waiting_queue)[2]
                assigned = allocate(tables, w_req, cur_time)
                if assigned:
                    assign(served_requests, waiting_queue, miss_queue, event_queue, event_count, tables, service_level_X, served_within_X, total_wait, max_wait, normal_served_count, w_req)
                else:
                    #update v1.5.0 我们决定保留先到先得的原则，防止小顾客一直拆散大桌的情况
                    heapq.heappush(waiting_queue, (w_req.vip, w_req.arrival, w_req))  # 重新加入等待队列（VIP 插队首，普通加队尾）
                    break   # 无法继续分配，跳出
            # 记录等待队列长度
            queue_lengths.append(len(waiting_queue))
            max_queue_length = max(max_queue_length, len(waiting_queue))

        # ---------- 到达事件 ----------
        elif ev_type == 'arrival':
            req = ev_req

            # Oscar：这部分是废话
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
                    if req.vip == 0:
                        normal_served_count += 1
                else:
                    # 理论上不会发生，因为预留已保证
                    raise RuntimeError(f"预订顾客 {req.index} 预留冲突")
                continue

            # update v1.5.0 重写过号逻辑：只有comeback 的过号顾客才会被处理
            if req.miss == 1 and req.comeback == 1:
                req.wait_time = 0  # 过号后重新计算等待时间
                req.arrival = req.arrival + 5 #简化处理
                miss_queue.append(req)
                # missqueue暂时使用简单队列
                continue 

            if waiting_queue or miss_queue and not req.vip:
                # 如果有等待队列或过号队列，先加入等待队列（VIP 插队首，普通加队尾）
                heapq.heappush(waiting_queue, (req.vip, req.arrival, req))
                # 记录等待队列长度
                queue_lengths.append(len(waiting_queue))
                max_queue_length = max(max_queue_length, len(waiting_queue))
                continue

            # update v1.5.0 重写分配逻辑，使用 allocate 函数统一处理分配，避免重复代码
            assigned = allocate(tables, req, req.arrival)
            if assigned:
                assign(served_requests, waiting_queue, miss_queue, event_queue, event_count, tables, service_level_X, served_within_X, total_wait, max_wait, normal_served_count, req)
            else:
                #update v1.5.0 我们决定保留先到先得的原则，防止小顾客一直拆散大桌的情况
                heapq.heappush(waiting_queue, (req.vip, req.arrival, req))  # 重新加入等待队列（VIP 插队首，普通加队尾）

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
