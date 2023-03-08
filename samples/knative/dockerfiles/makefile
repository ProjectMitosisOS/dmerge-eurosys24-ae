NAME=caribouf
BUILD_IMG=cpython-build
BASE_IMG=cpython-base
DMERGE_IMG=dmerge-base
DMERGE_DEVICE_PATH=/dev/mitosis-syscalls
_ACCESS_TOKEN=

build:
	docker build --build-arg ACCESS_TOKEN=${_ACCESS_TOKEN} -f Dockerfile-${BUILD_IMG} -t ${NAME}/${BUILD_IMG} .
	#docker push ${NAME}/${BUILD_IMG}

base-img:
	docker build -f Dockerfile-${BASE_IMG} -t ${NAME}/${BASE_IMG} ../../../deps/
	#docker push ${NAME}/${BUILD_IMG}

dmerge-img:
	docker build -f Dockerfile-${DMERGE_IMG} -t ${NAME}/${DMERGE_IMG} ../../../pyx

# Tempory containers for testing
test-build:
	docker run --rm -it ${NAME}/${BUILD_IMG} /bin/bash

test-base:
	docker run --rm -it ${NAME}/${BASE_IMG} /bin/bash

# Please insmod the dmerge module before running it
test-dmerge-base:
	docker run -e LD_PRELOAD=/usr/local/share/libmalloc_wrapper.so --rm --device=${DMERGE_DEVICE_PATH} -it ${NAME}/${DMERGE_IMG} /bin/bash