KNATIVE_EVENTING_VERSION=1.7.3

kubectl apply -f yaml/eventing-crds.yaml

kubectl apply -f yaml/eventing-core.yaml


# Install default in-memory channel (not suitable for production)
kubectl apply -f yaml/in-memory-channel.yaml

# Install default Broker (essential for broker messaging)
kubectl apply -f yaml/mt-channel-broker.yaml

