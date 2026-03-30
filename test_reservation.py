from dataclasses import dataclass, field
from typing import List, Tuple, Optional

@dataclass
class Request:
    index: int
    people: int
    arrival: int
    duration: int
    share: int
    miss: int
    comeback: int
    vip: int
    reserved: int
    table: Optional['Table'] = None
    wait_time: int = 0
    leave_time: int = 0

@dataclass
class Table:
    index: int
    max_people: int
    cur_people: int = 0
    customers: List[Request] = field(default_factory=list)
    reserved_slots: List[Tuple[int, int]] = field(default_factory=list)

def allocate_reserved_tables(requests: List[Request], tables: List[Table]):
    reserved_reqs = [r for r in requests if r.reserved == 1]
    reserved_reqs.sort(key=lambda x: (-x.people, x.arrival))
    assigned = {}
    for req in reserved_reqs:
        # 预订顾客必须预留整桌：选择能容纳该人数的最小桌子
        candidates = [t for t in tables if t.max_people >= req.people]
        candidates.sort(key=lambda t: (t.max_people, t.index))
        chosen = None
        for t in candidates:
            conflict = False
            for rs, re in t.reserved_slots:
                if not (re <= req.arrival or rs >= req.arrival + req.duration):
                    conflict = True
                    break
            if not conflict:
                chosen = t
                break
        if chosen is None:
            raise RuntimeError(f"无法为预订顾客 {req.index} 分配桌子")
        chosen.reserved_slots.append((req.arrival, req.arrival + req.duration))
        assigned[req.index] = chosen
    return assigned

def test_reservation():
    """测试预订预留整桌功能"""
    # 创建桌子：2张2人桌、1张4人桌
    tables = [
        Table(0, 2),
        Table(1, 2),
        Table(2, 4)
    ]
    
    # 创建预订顾客
    requests = [
        Request(1, 2, 100, 60, 1, 0, 0, 0, 1),  # 预订2人，应分配2人桌
        Request(2, 1, 120, 30, 1, 0, 0, 0, 1),  # 预订1人，应分配2人桌（最小可用）
        Request(3, 4, 140, 90, 1, 0, 0, 0, 1),  # 预订4人，应分配4人桌
    ]
    
    assigned = allocate_reserved_tables(requests, tables)
    
    print("预订分配结果：")
    for req_idx, table in assigned.items():
        req = next(r for r in requests if r.index == req_idx)
        print(f"  顾客{req_idx} ({req.people}人) -> 桌子{table.index} (容量{table.max_people}人)")
        print(f"    预留时间段: {table.reserved_slots}")
    
    # 验证：
    # 1. 每个预订顾客都分配了整张桌子（独占）
    # 2. 选择的是能容纳该人数的最小桌子
    print("\n验证结果：")
    
    # 顾客1（2人）应该分配2人桌
    table1 = assigned[1]
    if table1.max_people == 2:
        print("✓ 顾客1（2人）正确分配到2人桌")
    else:
        print(f"✗ 顾客1（2人）错误分配到{table1.max_people}人桌")
    
    # 顾客2（1人）应该分配2人桌（最小可用）
    table2 = assigned[2]
    if table2.max_people == 2:
        print("✓ 顾客2（1人）正确分配到2人桌（最小可用桌）")
    else:
        print(f"✗ 顾客2（1人）错误分配到{table2.max_people}人桌")
    
    # 顾客3（4人）应该分配4人桌
    table3 = assigned[3]
    if table3.max_people == 4:
        print("✓ 顾客3（4人）正确分配到4人桌")
    else:
        print(f"✗ 顾客3（4人）错误分配到{table3.max_people}人桌")
    
    # 验证预留区间已记录
    total_slots = sum(len(t.reserved_slots) for t in tables)
    if total_slots == 3:
        print("✓ 所有预订都已记录预留区间")
    else:
        print(f"✗ 预留区间数量错误：{total_slots}")

if __name__ == "__main__":
    test_reservation()
