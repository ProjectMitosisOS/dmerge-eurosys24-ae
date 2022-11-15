# shellcheck disable=SC2046
docker rmi -f  `docker images | grep 'caribouf' | awk '{print $3}'`
docker rmi -f  `docker images | grep '<none>' | awk '{print $3}'`
