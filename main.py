from dataclasses import dataclass
from datetime import datetime
from queue import Queue

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

    wait_time: int = 0 # for statistics

@dataclass() 
class table: # 关于这个 class 有没有必要还有待商榷
    index: int
    max_people: int
    cur_people: int = 0
    customers: list = []

    def seat(self, req: request, return_cnt, cur_time):
        req.table = self.index
        req.leave = req.arrival + req.duration
        req.wait_time = cur_time - req.arrival

        self.cur_people += req.people
        if self.customers is None:
            self.customers = []
        self.customers.append(req)

        return_cnt += 1

def create_request_from_csv(csv_row: list) -> request:
    # 原来写在 main 里有点屎山，遂独立
    index, people, arrival, duration, share, miss, comeback = csv_row
    
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

    with open("reservation.csv",'r') as f:
        for line in f:
            pass
        # 还没想好怎么写，到时候再说

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
    
    # 模拟
    for req in requests:
        cur_time = req.arrival
        # 先让之前的客人走，遍历桌子比遍历人清晰一些
        while req.table == -1 and cur_time <= 1000000:
            for t in tables:
                for c in t.customers:
                    if c.leave <= cur_time:
                        t.cur_people -= c.people
                        t.customers.remove(c)

                # 如果这个桌子走干净了，就让不让拼桌的来
                if t.cur_people == 0:
                    for r in noshare_request:
                        if r.people == t.max_people: # 这里保证队伍中的顾客一定在 curtime 之前到
                            t.seat(r, return_cnt, cur_time)
                            noshare_request.remove(r)
                            break

            if req.share:
                # 哪怕他愿意拼桌还是要优先给合适的
                for t in tables:
                    if t.cur_people == 0 and t.max_people == req.people:
                        t.seat(req, return_cnt, cur_time)
                        break
                else:
                    # 如果没有，找一个剩下位置最小的桌子
                    target_table = None
                    for t in tables:
                        if t.max_people - t.cur_people >= req.people:
                            if target_table is None or (t.max_people - t.cur_people < target_table.max_people - target_table.cur_people):
                                target_table = t
                    if target_table is not None:
                        target_table.seat(req, return_cnt, cur_time)
                    else:
                        if req.people > max_table_people:
                            req.table = -2
                            # 错误数据，直接丢弃
                            break
                        else:
                            cur_time +=1 # 这里简单处理了，也可以找下一个完成的 request
            if req.share == 0:
                for t in tables:
                    if t.cur_people == 0 and t.max_people == req.people:
                        t.seat(req, return_cnt, cur_time)
                        break
                else:
                    noshare_request.append(req)
                    break

        if return_cnt == 3:
            return_cnt = 0
            #处理过号
            pass

    # 处理剩余request
    for req in requests:
        pass

    # 处理剩余过号
    for req in return_request:
        pass
    # 数据统计

    # 文件输出

if __name__ == "__main__":
    main()