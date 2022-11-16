IMG_NAME=caribouf/ml-pipeline
URL=http://ml-pipeline.default.127.0.0.1.sslip.io


build-img:
	docker build -t $(IMG_NAME) .
	docker push $(IMG_NAME)

clean-img:
	docker rmi -f  `docker images | grep '<none>' | awk '{print $3}'`
# kubectl -n default get broker default-broker


deploy-broker:
	kubectl apply -f broker.yaml

deploy-app:
	kubectl apply -f service.yaml

trigger:
	curl -v ${URL} \
	-X POST \
    -H "Ce-Id: 536808d3-88be-4077-9d7a-a3f162705f79" \
    -H "Ce-Specversion: 1.0" \
    -H "Ce-Type: dev.knative.samples.mlpipeline" \
    -H "Ce-Source: ping" \
    -H "Content-Type: application/json" \
    -d '{"msg":"Hello World from the curl pod."}'


run:
	curl -v http://broker-ingress.knative-eventing.svc.cluster.local/default/default-broker  \
    	-X POST \
        -H "Ce-Id: 536808d3-88be-4077-9d7a-a3f162705f79" \
        -H "Ce-Specversion: 1.0" \
        -H "Ce-Type: dev.knative.sources.ping" \
        -H "Ce-Source: ping-pong" \
        -H "Content-Type: application/json" \
        -d '{"msg":"Hello World from the curl pod."}'