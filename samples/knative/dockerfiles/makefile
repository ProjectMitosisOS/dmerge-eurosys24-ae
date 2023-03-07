NAME=caribouf
BUILD_IMG=cpython-build
BASE_IMG=cpython-base
_ACCESS_TOKEN=

build:
	docker build --build-arg ACCESS_TOKEN=${_ACCESS_TOKEN} -f Dockerfile-${BUILD_IMG} -t ${NAME}/${BUILD_IMG} .
	#docker push ${NAME}/${BUILD_IMG}

base:
	docker build -f Dockerfile-${BASE_IMG} -t ${NAME}/${BASE_IMG} .
	#docker push ${NAME}/${BASE_IMG}

test-build:
	docker run --rm -it ${NAME}/${BUILD_IMG} /bin/bash

test-base:
	docker run --rm -it ${NAME}/${BASE_IMG} /bin/bash