"""
Restaurant Queue Simulator - Local UI Server
=============================================
运行方式：python app.py
然后在浏览器打开 http://localhost:5000

本文件会直接导入同目录下的 main.py（原项目文件），不修改任何原有代码。
"""

import sys
import os
import json
import csv
import io
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

# ─── 动态导入原项目的 main.py ───────────────────────────────────────────────
# app.py 需要放在与 main.py 同一目录下
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from main import Request, Table, parse_time, allocate_reserved_tables, allocate, simulate
    print("✅ 成功导入 main.py 中的模拟引擎")
except ImportError as e:
    print(f"❌ 无法导入 main.py: {e}")
    print("请确保 app.py 与 main.py 在同一目录下")
    sys.exit(1)

# ─── Flask 应用 ──────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=str(SCRIPT_DIR))
CORS(app)


# ─── 工具函数 ─────────────────────────────────────────────────────────────────
def build_tables(table_config: list) -> list:
    """将 [{count, capacity}, ...] 展开为 Table 对象列表"""
    tables = []
    for item in table_config:
        count = int(item["count"])
        capacity = int(item["capacity"])
        for _ in range(count):
            tables.append(Table(len(tables), capacity))
    return tables


def build_requests(requests_data: list) -> list:
    """将请求字典列表转换为 Request 对象列表"""
    reqs = []
    for r in requests_data:
        req = Request(
            index=int(r["index"]),
            people=int(r["people"]),
            arrival=parse_time(str(r["arrival"])),
            duration=int(r["duration"]),
            share=int(r["share"]),
            miss=int(r["miss"]),
            comeback=int(r["comeback"]),
            vip=int(r["vip"]),
            reserved=int(r["reserved"]),
        )
        reqs.append(req)
    return reqs


def get_per_table_util(tables: list, served_requests: list, total_time: int) -> list:
    """计算每张桌子的利用率（需要在 simulate 后调用）"""
    # 注意：simulate 函数内部已经计算了 table_busy_time，但没有返回
    # 我们在这里通过 served_requests 重新计算
    table_busy = {}
    for req in served_requests:
        if req.table is not None:
            tid = req.table.index
            table_busy[tid] = table_busy.get(tid, 0) + req.duration

    result = []
    for t in tables:
        busy = table_busy.get(t.index, 0)
        util = (busy / total_time * 100) if total_time > 0 else 0
        result.append({
            "table_id": t.index + 1,
            "capacity": t.max_people,
            "utilization": round(util, 1),
            "busy_time": busy,
        })
    return result


def get_customer_wait_times(served_requests: list) -> list:
    """提取每位顾客的等待时间"""
    return [
        {"index": r.index, "people": r.people, "wait_time": r.wait_time, "vip": r.vip}
        for r in served_requests
    ]


# ─── 输入校验 ─────────────────────────────────────────────────────────────────

def validate_table_config(table_config: list) -> list:
    """Return a list of error strings; empty means valid."""
    errors = []
    if not table_config:
        errors.append("tableConfig must not be empty")
        return errors
    for i, item in enumerate(table_config):
        try:
            count = int(item["count"])
            capacity = int(item["capacity"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"tableConfig[{i}]: 'count' and 'capacity' must be integers")
            continue
        if count <= 0:
            errors.append(f"tableConfig[{i}]: count must be >= 1, got {count}")
        if capacity <= 0:
            errors.append(f"tableConfig[{i}]: capacity must be >= 1, got {capacity}")
    return errors


def validate_requests(requests_data: list, max_capacity: int) -> list:
    """Return a list of error strings; empty means valid."""
    from datetime import datetime as _dt
    errors = []
    if not requests_data:
        errors.append("requests must not be empty")
        return errors
    seen_indices = set()
    for i, r in enumerate(requests_data):
        prefix = f"requests[{i}] (index={r.get('index', '?')})"
        # index
        try:
            idx = int(r["index"])
            if idx in seen_indices:
                errors.append(f"{prefix}: duplicate index {idx}")
            seen_indices.add(idx)
        except (KeyError, TypeError, ValueError):
            errors.append(f"{prefix}: 'index' must be an integer")
        # people
        try:
            people = int(r["people"])
            if people <= 0:
                errors.append(f"{prefix}: people must be >= 1, got {people}")
            elif people > max_capacity:
                errors.append(f"{prefix}: people ({people}) exceeds max table capacity ({max_capacity})")
        except (KeyError, TypeError, ValueError):
            errors.append(f"{prefix}: 'people' must be a positive integer")
        # arrival
        try:
            _dt.strptime(str(r["arrival"]).strip(), "%Y%m%d%H%M%S")
        except (KeyError, TypeError, ValueError):
            errors.append(f"{prefix}: 'arrival' must be in YYYYMMDDHHMMSS format")
        # duration
        try:
            dur = int(r["duration"])
            if dur <= 0:
                errors.append(f"{prefix}: duration must be >= 1, got {dur}")
        except (KeyError, TypeError, ValueError):
            errors.append(f"{prefix}: 'duration' must be a positive integer")
        # binary fields
        for field in ("share", "miss", "comeback", "vip", "reserved"):
            try:
                val = int(r[field])
                if val not in (0, 1):
                    errors.append(f"{prefix}: '{field}' must be 0 or 1, got {val}")
            except (KeyError, TypeError, ValueError):
                errors.append(f"{prefix}: '{field}' must be 0 or 1")
        # logical constraint: comeback requires miss
        try:
            if int(r.get("comeback", 0)) == 1 and int(r.get("miss", 0)) == 0:
                errors.append(f"{prefix}: comeback=1 requires miss=1")
        except (TypeError, ValueError):
            pass
    return errors


# ─── API 路由 ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """提供 ui.html 界面"""
    return send_from_directory(str(SCRIPT_DIR), "ui.html")


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """
    运行模拟
    请求体 JSON:
    {
        "tableConfig": [{"count": 5, "capacity": 2}, ...],
        "requests": [{"index":1,"people":2,"arrival":"20260101120000","duration":30,
                      "share":1,"miss":0,"comeback":0,"vip":0,"reserved":0}, ...]
    }
    """
    try:
        data = request.get_json(force=True)
        table_config = data.get("tableConfig", [])
        requests_data = data.get("requests", [])

        # ── validate table config first ──
        table_errors = validate_table_config(table_config)
        if table_errors:
            return jsonify({"success": False, "error": "Invalid table configuration",
                            "details": table_errors}), 400

        max_capacity = max(int(t["capacity"]) for t in table_config)

        # ── validate requests ──
        req_errors = validate_requests(requests_data, max_capacity)
        if req_errors:
            return jsonify({"success": False, "error": "Invalid request data",
                            "details": req_errors}), 400

        # 构建对象
        tables = build_tables(table_config)
        reqs = build_requests(requests_data)

        # 运行模拟
        stats = simulate(reqs, tables)

        # 提取每张桌子利用率和每位顾客等待时间
        # 从 reqs 中找出已服务的顾客（table 不为 None 说明已入座）
        served = [r for r in reqs if r.table is not None]
        per_table = get_per_table_util(tables, served, stats["total_time"])
        wait_times = get_customer_wait_times(served)

        return jsonify({
            "success": True,
            "results": {
                "avg_wait": round(stats["avg_wait"], 2),
                "max_wait": stats["max_wait"],
                "max_queue_len": stats["max_queue_len"],
                "served": stats["served"],
                "table_util": round(stats["table_util"], 1),
                "service_level": round(stats["service_level"], 1),
                "total_time": stats["total_time"],
                "per_table_utilization": per_table,
                "customer_wait_times": wait_times,
            }
        })

    except RuntimeError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "trace": traceback.format_exc()}), 500


@app.route("/api/presets", methods=["GET"])
def api_presets():
    """
    返回所有预置测试用例（request1.csv ~ request10.csv）
    同时返回对应的餐桌配置（restaurant1.csv ~ restaurant10.csv，若存在）
    """
    presets = []
    for i in range(1, 11):
        req_file = SCRIPT_DIR / f"request{i}.csv"
        rest_file = SCRIPT_DIR / f"restaurant{i}.csv"

        if not req_file.exists():
            continue

        # 读取请求
        requests_data = []
        try:
            with open(req_file, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) < 9:
                        continue
                    idx, peo, arr, dur, share, miss, comeback, vip, res = parts
                    requests_data.append({
                        "index": int(idx),
                        "people": int(peo),
                        "arrival": arr.strip(),
                        "duration": int(dur),
                        "share": int(share),
                        "miss": int(miss),
                        "comeback": int(comeback),
                        "vip": int(vip),
                        "reserved": int(res),
                    })
        except Exception as e:
            continue

        # 读取餐桌配置（若存在）
        table_config = []
        if rest_file.exists():
            try:
                with open(rest_file, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split(",")
                        if len(parts) >= 2:
                            table_config.append({
                                "count": int(parts[0]),
                                "capacity": int(parts[1]),
                            })
            except Exception:
                pass

        # 返回结构化元数据，由前端根据语言动态生成描述
        n = len(requests_data)
        has_vip = any(r["vip"] for r in requests_data)
        has_reserved = any(r["reserved"] for r in requests_data)
        has_miss = any(r["miss"] for r in requests_data)

        presets.append({
            "id": i,
            "name": f"Request {i}",
            "count": n,
            "hasVip": has_vip,
            "hasReserved": has_reserved,
            "hasMiss": has_miss,
            "requests": requests_data,
            "tableConfig": table_config,
        })

    return jsonify({"success": True, "presets": presets})


@app.route("/api/export", methods=["POST"])
def api_export():
    """
    导出模拟结果为 CSV
    请求体: { "results": {...}, "requests": [...] }
    """
    try:
        data = request.get_json(force=True)
        results = data.get("results", {})
        requests_data = data.get("requests", [])

        output = io.StringIO()
        writer = csv.writer(output)

        # 统计摘要
        writer.writerow(["=== Simulation Summary ==="])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Average Wait Time (min)", results.get("avg_wait", "")])
        writer.writerow(["Max Wait Time (min)", results.get("max_wait", "")])
        writer.writerow(["Peak Queue Length", results.get("max_queue_len", "")])
        writer.writerow(["Groups Served", results.get("served", "")])
        writer.writerow(["Table Utilization (%)", results.get("table_util", "")])
        writer.writerow(["Service Level - within 10min (%)", results.get("service_level", "")])
        writer.writerow(["Total Simulation Time (min)", results.get("total_time", "")])
        writer.writerow([])

        # 每位顾客等待时间
        wait_times = results.get("customer_wait_times", [])
        if wait_times:
            writer.writerow(["=== Customer Wait Times ==="])
            writer.writerow(["Request Index", "People", "Wait Time (min)", "VIP"])
            for r in wait_times:
                writer.writerow([r["index"], r["people"], r["wait_time"], "Yes" if r["vip"] else "No"])
            writer.writerow([])

        # 每张桌子利用率
        per_table = results.get("per_table_utilization", [])
        if per_table:
            writer.writerow(["=== Table Utilization ==="])
            writer.writerow(["Table ID", "Capacity", "Utilization (%)", "Busy Time (min)"])
            for t in per_table:
                writer.writerow([t["table_id"], t["capacity"], t["utilization"], t.get("busy_time", "")])
            writer.writerow([])

        # 原始请求数据
        if requests_data:
            writer.writerow(["=== Input Requests ==="])
            writer.writerow(["Index", "People", "Arrival", "Duration", "Share", "Miss", "Comeback", "VIP", "Reserved"])
            for r in requests_data:
                writer.writerow([
                    r["index"], r["people"], r["arrival"], r["duration"],
                    r["share"], r["miss"], r["comeback"], r["vip"], r["reserved"]
                ])

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name="simulation_results.csv",
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ─── 启动 ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  🍽  Restaurant Queue Simulator - Local UI")
    print("=" * 55)
    print(f"  项目目录: {SCRIPT_DIR}")
    print(f"  请在浏览器打开: http://localhost:5000")
    print("  按 Ctrl+C 停止服务器")
    print("=" * 55)
    app.run(host="127.0.0.1", port=5000, debug=False)
