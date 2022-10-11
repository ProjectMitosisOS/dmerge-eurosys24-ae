### Core components
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.7.2/serving-crds.yaml

kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.7.2/serving-core.yaml

### Network
kubectl apply -f https://github.com/knative/net-kourier/releases/download/knative-v1.7.0/kourier.yaml

kubectl patch configmap/config-network \
--namespace knative-serving \
--type merge \
--patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}'

kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.7.2/serving-default-domain.yaml

kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.7.2/serving-hpa.yaml
