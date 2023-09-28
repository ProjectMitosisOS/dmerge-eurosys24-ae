#!/usr/bin/env bash

user="eurosys24ae"
target=("val06" "val07")
PROJECT_PATH=/home/${user}/projects/dmerge

cd $PROJECT_PATH
source ~/.cargo/env ; make km
cd $PROJECT_PATH/ae_scripts ; rm -rf tmp ; mkdir -p tmp/dmerge-kms
cp $PROJECT_PATH/dmerge-kms/heap.ko tmp/dmerge-kms/
cp -r $PROJECT_PATH/samples tmp/
cp -r $PROJECT_PATH/deps tmp/
cp -r $PROJECT_PATH/dmerge-user-libs tmp/
cp $PROJECT_PATH/makefile tmp/
cp $PROJECT_PATH/ae_scripts/cargo_config/config tmp/

for machine in ${target[*]}
do
    ssh $user@$machine "mkdir -p projects/dmerge; mkdir ~/.cargo"
    rsync -i -rtuv \
          $PWD/tmp/dmerge-kms \
          $PWD/tmp/makefile \
          $PWD/tmp/samples \
          $PWD/tmp/deps \
          $PWD/tmp/dmerge-user-libs \
          $user@$machine:~/projects/dmerge
    rsync -i -rtuv \
          $PWD/tmp/config \
          $user@$machine:~/.cargo/
done
