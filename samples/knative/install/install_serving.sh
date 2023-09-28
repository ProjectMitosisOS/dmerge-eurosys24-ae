### Core components
kubectl apply -f yaml/serving-crds.yaml

kubectl apply -f yaml/serving-core.yaml

### Network
kubectl apply -f yaml/kourier.yaml

kubectl patch configmap/config-network \
--namespace knative-serving \
--type merge \
--patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}'

# kubectl --namespace kourier-system get service kourier
# Get the IP of cluster (e.g. curl -H "Host: hello.default.example.com " http://10.107.7.121)

kubectl apply -f yaml/serving-hpa.yaml
