#!/usr/bin/env bash

user="eurosys24ae"
target=("val06" "val07")
PROJECT_PATH=/home/${user}/projects/dmerge

cd $PROJECT_PATH
source ~/.cargo/env ; make km
cd $PROJECT_PATH/ae_scripts ; rm -rf tmp ; mkdir -p tmp/dmerge-kms
cp $PROJECT_PATH/dmerge-kms/heap.ko tmp/dmerge-kms/
cp $PROJECT_PATH/makefile tmp/

for machine in ${target[*]}
do
    ssh $user@$machine "mkdir -p projects/dmerge"
    rsync -i -rtuv \
          $PWD/tmp/dmerge-kms \
          $PWD/tmp/makefile \
          $user@$machine:~/projects/dmerge

done
