import subprocess
import re
import numpy as np

import argparse

parser = argparse.ArgumentParser("log analyser")
parser.add_argument("--pod_name", help="Traget pod name", type=str)
parser.add_argument("--app_name", help="Traget pod name", type=str)
args = parser.parse_args()
pod_name = args.pod_name


def filter_log_lines(log_lines):
    return [line.strip() for line in log_lines if line.startswith('Part@')]


def match_time(line, pattern):
    matched = re.search(pattern, line)
    if matched:
        return float(matched[1])
    else:
        return None


def calculate(log_lines):
    pattern = r"Part@ (\w+) passed (\d+\.*\d+) ms"
    stages = {}
    cur_tick_mss = []
    event_count = 0

    for line in log_lines:
        matches = re.findall(pattern, line)
        if len(matches) == 0:
            continue
        else:
            matches = matches[-1]
        stage_name, value = matches[0], float(matches[1])
        if stage_name == 'cur_tick_ms':
            cur_tick_mss.append(value)
            event_count += 1
        else:
            stage_time = value
            if stage_name in stages:
                stages[stage_name].append(stage_time)
            else:
                stages[stage_name] = [stage_time]

    percentile = 5
    for key in stages:
        data = stages[key]
        low, high = np.percentile(data, [percentile, 100 - percentile])  # Remove 10% data
        stages[key] = [x for x in data if low <= x <= high]

    avg_dict = {}
    for key, value in stages.items():
        avg_dict[key] = np.mean(value)
    throughput = event_count / ((max(cur_tick_mss) - min(cur_tick_mss)) / 1000)

    tail_delays = []
    if 'stage_time' in stages:
        try:
            tail_delays.append(np.percentile(stages['stage_time'], 99))
            tail_delays.append(np.percentile(stages['stage_time'], 95))
            tail_delays.append(np.percentile(stages['stage_time'], 90))
            tail_delays.append(np.percentile(stages['stage_time'], 50))
        except Exception:
            pass
    return avg_dict, throughput, tail_delays


kubectl_command = f"kubectl logs {pod_name} user-app".split()
print(kubectl_command)
log_lines = subprocess.run(kubectl_command, stdout=subprocess.PIPE).stdout.decode().splitlines()

filtered_log_lines = filter_log_lines(log_lines)
avg_dict, throughput, tail_delays = calculate(filtered_log_lines)
for stage, avg in avg_dict.items():
    print(f"Avg {stage}\n\t{avg} ms")
print(f"throughput\n\t{throughput} qps")
print("tail_delays (P99, P95, P90, P50)\n\t", tail_delays)
