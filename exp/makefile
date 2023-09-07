SHELL:=/bin/bash
#APP_DIR=test
#APP_DIR=thpt
APP_DIR=micro
#APP_DIR=finra
#APP_DIR=digital-minist
#APP_DIR=ml-pipeline
#APP_DIR=wordcount
IMG_NAME=val01:5000/dmerge-${APP_DIR}
COMMON_PATH=common
POD_NAME=
LOOP=0
THPT_OUT=es

local-test:
	docker run --rm -it ${IMG_NAME} /bin/bash

build-img:
	docker build -t $(IMG_NAME) ${APP_DIR}
	docker push $(IMG_NAME)

clean-img:
	docker rmi -f  `docker images | grep '<none>' | awk '{print $3}'`

# kubectl -n default get broker default-broker
clean-terminating-pods:
	kubectl get pods | grep Terminating | awk '{print $1}' | xargs kubectl delete pod

deploy-meta:
	kubectl apply -f ${COMMON_PATH}/metric-server.yaml
	kubectl apply -f ${COMMON_PATH}/meta.yaml
	kubectl apply -f ${COMMON_PATH}/redis.yaml
	kubectl apply -f ${COMMON_PATH}/minio.yaml

undeploy-meta:
	kubectl delete -f ${COMMON_PATH}/metric-server.yaml
	kubectl delete -f ${COMMON_PATH}/meta.yaml
	kubectl delete -f ${COMMON_PATH}/redis.yaml
	kubectl delete -f ${COMMON_PATH}/minio.yaml


dps: # device plugins
	kubectl apply -f ${COMMON_PATH}/device-plugin.yaml

udps: # unmount device plugins
	kubectl delete -f ${COMMON_PATH}/device-plugin.yaml


upapp:
	kubectl apply -f ${APP_DIR}/service.yaml

downapp:
	kubectl delete -f ${APP_DIR}/service.yaml

curl:
	kubectl exec -it curl -- curl -v http://start-kn-sequence-0-kn-channel.default.svc.cluster.local  \
    -X POST \
    -H "Ce-Id: 536808d3-88be-4077-9d7a-a3f162705f79" \
    -H "Ce-Specversion: 1.0" \
    -H "Ce-Type: dev.knative.sources.ping" \
    -H "Ce-Source: ping-pong" \
    -H "Content-Type: application/json" \
    -d '{"loop":"${LOOP}"}'

profile:
	python log_analyser.py --pod_name=${POD_NAME} --app_name=${APP_DIR}-out

hey:
	kubectl exec -it hey -- hey -q 1 -c 50 -z 10s -m POST -T 'application/json' \
                                -d '{"loop":"${LOOP}"}' \
                                -H 'Ce-Id: 536808d3-88be-4077-9d7a-a3f162705f79' \
                                -H 'Ce-Specversion: 1.0' \
                                -H 'Ce-Type: dev.knative.sources.ping' \
                                -H 'Ce-Source: ping-pong' \
                                 http://start-kn-sequence-0-kn-channel.default.svc.cluster.local

SHELL := /bin/bash


dt:
	kubectl apply -f thpt/dummy.yaml

udt:
	kubectl delete -f thpt/dummy.yaml

POD_NAME := $(shell kubectl get pods -l app=dummy -o name | shuf -n 1)

# scp -r lfm@val06:/tmp/thpt-lat-out/. out/
th:
	kubectl exec -it ${POD_NAME} -- \
        ./trigger_go/trigger --threads=10 --interval_ms=100 --run_time=60 --out_dir=tmp/${THPT_OUT} --concurrency=-1

# thpt with same concurrency
thc:
	kubectl exec -it ${POD_NAME} -- \
            ./trigger_go/trigger --threads=10 --interval_ms=100 --run_time=60 --out_dir=tmp/${THPT_OUT}_c --concurrency=90
