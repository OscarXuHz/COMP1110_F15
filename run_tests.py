"""
Test runner for restaurant queue simulation.
Loads request{i}.csv and restaurant{i}.csv, runs simulate(), saves output{i}.csv.
"""
import sys
import os
import copy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import Request, Table, load_requests, simulate


def load_restaurant(filename):
    """Load restaurant table configuration from CSV file."""
    tables = []
    with open(filename, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 2:
                continue
            count, cap = int(parts[0]), int(parts[1])
            for _ in range(count):
                tables.append(Table(len(tables), cap))
    return tables


def run_test(test_num):
    req_file = f'request{test_num}.csv'
    rest_file = f'restaurant{test_num}.csv'
    out_file = f'output{test_num}.csv'

    if not os.path.exists(req_file) or not os.path.exists(rest_file):
        print(f"Test {test_num}: SKIPPED (files not found)")
        return

    requests = load_requests(req_file)
    tables = load_restaurant(rest_file)

    stats = simulate(requests, tables)

    output_lines = [
        "Simulation Result:",
        "------------------",
        f"Average Wait Time: {stats['avg_wait']:.1f} min",
        f"Max Wait Time: {stats['max_wait']} min",
        f"Peak Queue Length: {stats['max_queue_len']}",
        f"Groups Served: {stats['served']}",
        f"Table Utilization: {stats['table_util']:.1f}%",
        f"Service Level (seated within 10 min): {stats['service_level']:.1f}%",
        f"Total Time: {stats['total_time']} min",
    ]

    output = '\n'.join(output_lines)

    with open(out_file, 'w') as f:
        f.write(output + '\n')

    print(f"=== Test {test_num} ===")
    print(output)
    print()


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    for i in range(1, 11):
        try:
            run_test(i)
        except Exception as e:
            print(f"=== Test {i} FAILED ===")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            print()
