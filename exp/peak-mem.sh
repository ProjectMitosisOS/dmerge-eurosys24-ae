#!/bin/bash

memory_usage() {
  pod_name=$1
  memory_usage=$(kubectl exec $pod_name --namespace=default -- bash -c "cat /sys/fs/cgroup/memory/memory.usage_in_bytes" | awk '{sum += $1} END {print sum}')
  echo $memory_usage
}

export -f memory_usage

total_memory=$(kubectl get pods --namespace=default -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | parallel -j+0 memory_usage | awk '{sum += $1} END {print sum}')

echo "Total memory usage: $((total_memory / (1024 * 1024))) MB"