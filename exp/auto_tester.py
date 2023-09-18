import os
import re
import subprocess
import time
import argparse
from kubernetes import client, config


def wait_for_pods():
    config.load_kube_config()  # Load Kubernetes configuration from default location
    v1 = client.CoreV1Api()
    n = 0
    while True:
        pods = v1.list_namespaced_pod('default').items
        status = [pod.status.phase == 'Running' and pod.metadata.deletion_timestamp is None for pod in pods]
        all_running = all(status)
        if all_running:
            break
        time.sleep(1)  # Wait for 5 seconds before checking again
        print(f'Waiting start for {n} second(s)')
        for pod, is_running in zip(pods, status):
            if pod.metadata.labels is not None:
                service_name = pod.metadata.labels.get('serving.knative.dev/service')
                if service_name is not None:
                    pod_status = 'Running' if is_running else 'Not Running'
                    print(f'\tService:\t{service_name}\tStatus:\t{pod_status}')
        n += 1


def trigger_workflow():
    subprocess.run('make curl', shell=True)


def fetch_workflow_time(service_name):
    config.load_kube_config()  # Load Kubernetes configuration from default location
    v1 = client.CoreV1Api()

    while True:
        pod_list = v1.list_namespaced_pod(namespace='default').items
        for pod in pod_list:
            if (pod.metadata.labels is not None and
                    pod.metadata.labels.get('serving.knative.dev/service') == service_name):
                log = v1.read_namespaced_pod_log(name=pod.metadata.name, namespace='default',
                                                 container='user-app')
                lines = log.split('\n')
                for line in lines:
                    pattern = r'workflow e2e time:\s+(\d+\.*\d+)'
                    match = re.search(pattern, line)
                    if match:
                        return float(match.group(1))
        time.sleep(1)


def deploy_pods(app_dir, eval_protocol):
    subprocess.run(f'kubectl apply -f {app_dir}/services/{eval_protocol}/service.yaml', shell=True)


def cleanup_pods(app_dir, eval_protocol):
    subprocess.run(f'kubectl delete -f {app_dir}/services/{eval_protocol}/service.yaml', shell=True)


def main():
    parser = argparse.ArgumentParser(description='Automate evaluation steps for a specific application and protocol.')
    parser.add_argument('--app_dir', help='The application name')
    parser.add_argument('--eval_protocol', help='The state transfer protocol')
    parser.add_argument('--profile_service', help='The name of the container service for log viewing')
    args = parser.parse_args()

    app_dir = args.app_dir
    protocol = args.eval_protocol
    sink_service_name = args.profile_service

    deploy_pods(app_dir, protocol)
    wait_for_pods()
    trigger_workflow()
    workflow_time = fetch_workflow_time(sink_service_name)
    print(f'App <{app_dir}> at Protocol <{protocol}> has end-to-end latency {workflow_time} ms')
    cleanup_pods(app_dir, protocol)


if __name__ == '__main__':
    main()
