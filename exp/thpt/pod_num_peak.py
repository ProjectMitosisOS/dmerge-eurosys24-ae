import os
import time
import csv
import argparse
from kubernetes import client, config

config.load_kube_config()

v1 = client.CoreV1Api()

# 解析命令行参数
parser = argparse.ArgumentParser(description='Get running pod count in Kubernetes cluster.')
parser.add_argument('--output', type=str, help='CSV output file name', default='pod_cnt')
parser.add_argument('--seconds', type=int, help='Number of seconds to run', default=60)
args = parser.parse_args()

out_path = args.output + '.csv'
run_time = args.seconds

if os.path.exists(out_path):
    os.remove(out_path)


def cur_tick_ms():
    return int(round(time.time() * 1000))


pods = v1.list_namespaced_pod(namespace='default', field_selector='status.phase=Running')
base_running_cnt = len(pods.items)
with open(out_path, mode='a') as file:
    writer = csv.writer(file)
    writer.writerow(['Seq', 'Cnt'])

start_time = time.time()
start_time_ms = cur_tick_ms()

while time.time() - start_time <= run_time:
    pods = v1.list_namespaced_pod(namespace='default', field_selector='status.phase=Running')
    running_count = len(pods.items)
    seq = int((cur_tick_ms() - start_time_ms) / 100)
    pod_cnt = 10 + (running_count - base_running_cnt) * 3
    print("Seq: {}, Number of running pods in default namespace: {}".format(seq, pod_cnt))

    with open(out_path, mode='a') as file:
        writer = csv.writer(file)
        writer.writerow([seq, pod_cnt])
    time.sleep(0.1)
