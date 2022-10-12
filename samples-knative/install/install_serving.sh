### Core components
kubectl apply -f yaml/serving-crds.yaml

kubectl apply -f yaml/serving-core.yaml

### Network
kubectl apply -f yaml/kourier.yaml

kubectl patch configmap/config-network \
--namespace knative-serving \
--type merge \
--patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}'

kubectl apply -f yaml/serving-default-domain.yaml

kubectl apply -f yaml/serving-hpa.yaml
