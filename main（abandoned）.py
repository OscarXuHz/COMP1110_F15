from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue
import heapq

@dataclass()
class request:
    index: int
    people: int
    arrival: int
    duration: int
    leave: int = 0 # 暂时置零
    share: int = 1 # willingness to share table
    
    table: int = -1
    miss: int = 0 # 是否过号
    comeback: int = 0 # 过号之后是否回来

    vip: int = 0 # VIP 标识，1=VIP 优先入座

    wait_time: int = 0 # for statistics

@dataclass() 
class table: # 关于这个 class 有没有必要还有待商榷
    index: int
    max_people: int
    cur_people: int = 0
    customers: list = field(default_factory=list)

    def seat(self, req: request, return_cnt, cur_time):
        req.table = self.index
        req.leave = cur_time + req.duration
        req.wait_time = cur_time - req.arrival

        self.cur_people += req.people
        if self.customers is None:
            self.customers = []
        self.customers.append(req)

        return_cnt += 1

def create_request_from_csv(csv_row: list) -> request:
    # 原来写在 main 里有点屎山，遂独立
    index, people, arrival, duration, share, miss, comeback = csv_row[:7]
    
    # 转换为时间戳，单位为分钟
    arrival_dt = datetime.strptime(arrival, '%Y%m%d%H%M%S')
    arrival_timestamp = int(arrival_dt.timestamp() / 60)
    
    return request(
        index=int(index),
        people=int(people),
        arrival=arrival_timestamp,
        duration=int(duration),
        share=int(share),
        miss=int(miss),
        comeback=int(comeback),
        leave=0  # 由 table.seat() 计算
    )

def main():
    requests = []
    tables = []
    return_request = [] # 过号队列
    noshare_request = []
    max_table_people = 0
    # restaurant = []
    
    table_count = 10 #餐桌种类

    # 数据读取
    with open('requests.csv', 'r') as f:
        for line in f:
            csv_row = line.strip().split(',')
            requests.append(create_request_from_csv(csv_row))

    # 假设餐厅的参数格式：每一行是“数量，对应人数“
    with open("restaurant.csv", 'r') as f:
        for line in f:
            count, people = line.strip().split(',')
            # restaurant.append((int(count), int(people)))
            for _ in range(int(count)):
                tables.append(table(len(tables), int(people)))
                if int(people) > max_table_people:
                    max_table_people = int(people)

    # reservation.csv 格式：index, people, arrival, duration, share
    # 预约顾客自动标记 vip=1，miss/comeback 默认为 0
    with open("reservation.csv", 'r') as f:
        for line in f:
            row = line.strip()
            if not row:
                continue
            parts = row.split(',')
            if len(parts) < 5:
                continue
            idx, people, arrival, duration, share = parts[:5]
            arrival_dt = datetime.strptime(arrival, '%Y%m%d%H%M%S')
            arrival_ts = int(arrival_dt.timestamp() / 60)
            requests.append(request(
                index=int(idx),
                people=int(people),
                arrival=arrival_ts,
                duration=int(duration),
                share=int(share),
                vip=1,
                leave=0
            ))

    if len(requests) == 0:
        # 特殊数据，忽略
        return 

    # 初始化部分
    requests.sort(key=lambda x: x.arrival)
    return_cnt = 0 # 计数器，每过三个普通叫一个过号
    # queues = [Queue() for _ in range(table_count)] # 为每种餐桌建一个队
    s_time = requests[0].arrival
    cur_time = s_time
    # 将所有时间转换为相对于第一个顾客的增量时间戳
    for req in requests:
        req.arrival = req.arrival - s_time
    
    # 队列设置: 按人数分为 1-2, 3-4, 5+ 三类
    queue_ranges = [(1, 2), (3, 4), (5, max(max_table_people, 99))]
    queues = {r: [] for r in queue_ranges}
    peak_queue_lengths = {r: 0 for r in queue_ranges}

    def get_queue_key(people):
        for r in queue_ranges:
            if r[0] <= people <= r[1]:
                return r
        return queue_ranges[-1]

    def find_best_table(people, share):
        best = None
        if share:
            for t in tables:
                avail = t.max_people - t.cur_people
                if avail >= people:
                    if best is None or avail < (best.max_people - best.cur_people):
                        best = t
        else:
            for t in tables:
                if t.cur_people == 0 and t.max_people >= people:
                    if best is None or t.max_people < best.max_people:
                        best = t
        return best

    def free_tables(time):
        for t in tables:
            leaving = [c for c in t.customers if 0 < c.leave <= time]
            for c in leaving:
                t.cur_people -= c.people
                t.customers.remove(c)

    def try_seat_all(time):
        nonlocal return_cnt
        progress = True
        while progress:
            progress = False
            # 3:1 ratio: 每服务3组普通顾客，服务1组过号顾客
            if return_cnt >= 3 and return_request:
                req = return_request[0]
                t = find_best_table(req.people, req.share)
                if t:
                    t.seat(req, return_cnt, time)
                    return_request.pop(0)
                    return_cnt = 0
                    progress = True
                    continue
            # 优先处理 VIP 顾客（按到达时间最早）
            vip_req, vip_key = None, None
            for key, q in queues.items():
                for r in q:
                    if r.vip and (vip_req is None or r.arrival < vip_req.arrival):
                        vip_req = r
                        vip_key = key
            if vip_req:
                t = find_best_table(vip_req.people, vip_req.share)
                if t:
                    t.seat(vip_req, return_cnt, time)
                    queues[vip_key].remove(vip_req)
                    return_cnt += 1
                    progress = True
                    continue
            # 从所有队列中找最早等待的普通顾客
            best_req, best_key = None, None
            for key, q in queues.items():
                if q and (best_req is None or q[0].arrival < best_req.arrival):
                    best_req = q[0]
                    best_key = key
            if best_req:
                t = find_best_table(best_req.people, best_req.share)
                if t:
                    t.seat(best_req, return_cnt, time)
                    queues[best_key].pop(0)
                    return_cnt += 1
                    progress = True
                else:
                    break

    # 事件驱动模拟
    ARRIVE, TABLE_FREE = 0, 1
    event_heap = []
    for i, req in enumerate(requests):
        heapq.heappush(event_heap, (req.arrival, ARRIVE, i))
    scheduled_frees = set()

    while event_heap:
        evt_time, evt_type, evt_idx = heapq.heappop(event_heap)
        cur_time = evt_time
        free_tables(cur_time)

        if evt_type == ARRIVE:
            req = requests[evt_idx]
            if req.people > max_table_people:
                req.table = -2
            elif req.miss and not req.comeback:
                req.table = -2
            elif req.miss and req.comeback:
                return_request.append(req)
            else:
                queues[get_queue_key(req.people)].append(req)

        for key in queues:
            peak_queue_lengths[key] = max(peak_queue_lengths[key], len(queues[key]))

        try_seat_all(cur_time)

        for t in tables:
            for c in t.customers:
                if c.leave > 0 and c.index not in scheduled_frees:
                    scheduled_frees.add(c.index)
                    heapq.heappush(event_heap, (c.leave, TABLE_FREE, c.index))

    # 处理剩余排队顾客
    while any(queues[k] for k in queues) or return_request:
        next_free = min((c.leave for t in tables for c in t.customers if c.leave > cur_time), default=float('inf'))
        if next_free == float('inf'):
            break
        cur_time = next_free
        free_tables(cur_time)
        prev = sum(1 for r in requests if r.table >= 0)
        try_seat_all(cur_time)
        if sum(1 for r in requests if r.table >= 0) == prev:
            break

    # 数据统计
    served = [r for r in requests if r.table >= 0]
    end_time = max((r.leave for r in served), default=0)
    total_time = end_time
    avg_wait = sum(r.wait_time for r in served) / len(served) if served else 0
    max_wait = max((r.wait_time for r in served), default=0)
    total_peak = sum(peak_queue_lengths.values())
    total_occupied = sum(r.duration for r in served)
    total_capacity = len(tables) * total_time if total_time > 0 else 1
    utilization = (total_occupied / total_capacity) * 100
    threshold = 15
    within = sum(1 for r in served if r.wait_time <= threshold)
    service_level = (within / len(served) * 100) if served else 0

    # 结果输出
    print("Simulation Result:")
    print("------------------")
    print(f"Total Time: {total_time} min")
    print(f"Groups Served: {len(served)}")
    print(f"Average Wait Time: {avg_wait:.1f} min")
    print(f"Max Wait Time: {max_wait} min")
    print(f"Peak Queue Length: {total_peak}")
    for key in queue_ranges:
        print(f"  Queue {key[0]}-{key[1]}: {peak_queue_lengths[key]}")
    print(f"Table Utilization: {utilization:.1f}%")
    print(f"Service Level (seated within {threshold} min): {service_level:.1f}%")

if __name__ == "__main__":
    main()
