IMG_NAME=val01:5000/dmerge-p2p

local-test:
	docker run --rm -it ${IMG_NAME} /bin/bash

build-img:
	docker build -t $(IMG_NAME) .
	docker push $(IMG_NAME)

clean-img:
	docker rmi -f  `docker images | grep '<none>' | awk '{print $3}'`

# kubectl -n default get broker default-broker
clean-terminating-pods:
	kubectl get pods | grep Terminating | awk '{print $1}' | xargs kubectl delete pod

deploy-meta:
	kubectl apply -f meta.yaml
	kubectl apply -f redis.yaml

dpapp:
	kubectl apply -f service.yaml

upapp:
	kubectl delete -f service.yaml

curl:
	kubectl exec -it curl -- curl -v http://broker-ingress.knative-eventing.svc.cluster.local/default/default-broker \
    -X POST \
    -H "Ce-Id: 536808d3-88be-4077-9d7a-a3f162705f79" \
    -H "Ce-Specversion: 1.0" \
    -H "Ce-Type: dev.knative.sources.ping" \
    -H "Ce-Source: ping-pong" \
    -H "Content-Type: application/json" \
    -d '{"mapper_num":"16"}'

template:
	curl -v http://broker-ingress.knative-eventing.svc.cluster.local/default/default-broker  \
    	-X POST \
        -H "Ce-Id: 536808d3-88be-4077-9d7a-a3f162705f79" \
        -H "Ce-Specversion: 1.0" \
        -H "Ce-Type: dev.knative.sources.ping" \
        -H "Ce-Source: ping-pong" \
        -H "Content-Type: application/json" \
        -d '{"mapper_num":"16"}'