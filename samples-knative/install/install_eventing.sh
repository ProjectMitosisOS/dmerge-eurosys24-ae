KNATIVE_EVENTING_VERSION=1.7.3

kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v${KNATIVE_EVENTING_VERSION}/eventing-crds.yaml

kubectl apply -f https://github.com/knative/eventing/releases/download/knative-v${KNATIVE_EVENTING_VERSION}/eventing-core.yaml


# Install default in-memory channel (not suitable for production)
kubectl apply -f "https://github.com/knative/eventing/releases/download/knative-v${KNATIVE_EVENTING_VERSION}/in-memory-channel.yaml"

# Install default Broker (essential for broker messaging)
kubectl apply -f "https://github.com/knative/eventing/releases/download/knative-v${KNATIVE_EVENTING_VERSION}/mt-channel-broker.yaml"

