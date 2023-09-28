KNATIVE_EVENTING_VERSION=1.7.3

kubectl delete -f yaml/in-memory-channel.yaml

kubectl delete -f yaml/mt-channel-broker.yaml

kubectl delete -f yaml/eventing-core.yaml

kubectl delete -f yaml/eventing-crds.yaml


