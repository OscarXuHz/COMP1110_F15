from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import heapq

# 简化测试：验证 VIP 插队逻辑
def test_vip_queue():
    """测试 VIP 插队到队首，普通顾客加队尾"""
    waiting_queue = []
    
    # 模拟场景：普通顾客1到达
    class MockReq:
        def __init__(self, idx, vip):
            self.index = idx
            self.vip = vip
    
    req1 = MockReq(1, 0)  # 普通顾客
    req2 = MockReq(2, 0)  # 普通顾客
    req3 = MockReq(3, 1)  # VIP
    req4 = MockReq(4, 0)  # 普通顾客
    req5 = MockReq(5, 1)  # VIP
    
    # 按顺序加入队列
    for req in [req1, req2, req3, req4, req5]:
        if req.vip == 1:
            waiting_queue.insert(0, req)  # VIP 插队首
        else:
            waiting_queue.append(req)      # 普通加队尾
    
    # 验证队列顺序
    print("等待队列顺序（应该 VIP 在前）：")
    for i, req in enumerate(waiting_queue):
        vip_str = "VIP" if req.vip == 1 else "普通"
        print(f"  位置{i}: 顾客{req.index} ({vip_str})")
    
    # 预期：VIP5, VIP3, 普通1, 普通2, 普通4
    expected = [5, 3, 1, 2, 4]
    actual = [req.index for req in waiting_queue]
    
    if actual == expected:
        print("\n✓ VIP 插队逻辑正确")
    else:
        print(f"\n✗ VIP 插队逻辑错误")
        print(f"  预期: {expected}")
        print(f"  实际: {actual}")

if __name__ == "__main__":
    test_vip_queue()
