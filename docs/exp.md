## Evaluation instructions

**Important to know**: All of the commands are ran on machine `val05`, which serves for master node in kubernates and control node in all experiments.

### 1. Common configurations before experiments.

Firstly, we have to setup kernel modules and kantive runtime extensions before to go.

#### Kernel modules

Please go to `ae_scripts` and activate the python virtenv to run the module `insmod`. Please setup your login password in environment variable `PASSWORD`.

```sh
# On val05
cd $PROJECT_PATH/ae_scripts
source env/bin/activate

export PASSWORD="" # Change to your login password
python bootstrap.py -f insmod.toml -u $USER -p $PASSWORD; sleep 1; python bootstrap.py -f full-connect.toml -u $USER -p $PASSWORD
```

Note: please ensure the path `/dev/mitosis-syscalls` (on worker nodes val06 and val07) is not a directory, otherwise the syscall layer would go wrong. If it is a directory, please run the recover commands as below:

```sh
# On val05
cd $PROJECT_PATH/ae_scripts
source env/bin/activate
python bootstrap.py -f rmmod.toml -u $USER -p $PASSWORD; python bootstrap.py -f recover-device.toml -u $USER -p $PASSWORD 
```



#### Knative extension

Please go to path `exp` and run as below:

```sh
# On val05
cd $PROJECT_PATH/exp
make deploy-meta
make dps
```

It will start all essential pods & plugins for knative. You can use `kubectl get pods -A | grep hostdev-device-dev-plugin` to see if all extensions are installed.

```sh
# On val05
$ kubectl get pods -A | grep hostdev-device-dev-plugin

kube-system        hostdev-device-dev-plugin-lqxdv                   1/1     Running   0              10d
kube-system        hostdev-device-dev-plugin-rkktf                   1/1     Running   0              10d
```



### 2. Microbenchmark

We are now going to reproduce evaluation result for E2E time in `Figure 11 (b)` 

```sh
# On val05
cd $PROJECT_PATH/exp
python auto_tester.py --app_dir=micro --eval_protocol=rpc --profile_service=sink # RPC
python auto_tester.py --app_dir=micro --eval_protocol=es --profile_service=sink # external storage
python auto_tester.py --app_dir=micro --eval_protocol=dmerge --profile_service=sink # Our system
```



### 3. Application evaluations

This evaluation part reproduce evaluation result in `Figure 12`.

Please run commands as below to generate all experiments data.

```sh
TODO:
```

After running all of these experiments, you can execute `make fig12` to plot the data result, and the outcome figure is in `out/fig12.png`.



#### FINRA

```sh
# On val05
cd $PROJECT_PATH/exp
python auto_tester.py --app_dir=finra --eval_protocol=rpc --profile_service=sink # Messaging
python auto_tester.py --app_dir=finra --eval_protocol=es --profile_service=sink # Shared Storage
python auto_tester.py --app_dir=finra --eval_protocol=dmerge --profile_service=sink # RMMap
```



#### ML training

```sh
# On val05
cd $PROJECT_PATH/exp
python auto_tester.py --app_dir=ml-pipeline --eval_protocol=rpc --profile_service=sink # Messaging
python auto_tester.py --app_dir=ml-pipeline --eval_protocol=es --profile_service=sink # Shared Storage
python auto_tester.py --app_dir=ml-pipeline --eval_protocol=dmerge --profile_service=sink # RMMap
```



#### ML prediction

```sh
# On val05
cd $PROJECT_PATH/exp
python auto_tester.py --app_dir=digital-minist --eval_protocol=rpc --profile_service=combine # Messaging
python auto_tester.py --app_dir=digital-minist --eval_protocol=es --profile_service=combine # Shared Storage
python auto_tester.py --app_dir=digital-minist --eval_protocol=dmerge --profile_service=combine # RMMap
```



#### Word count

```sh
# On val05
cd $PROJECT_PATH/exp
python auto_tester.py --app_dir=wordcount --eval_protocol=rpc --profile_service=reducer-0 # Messaging
python auto_tester.py --app_dir=wordcount --eval_protocol=es --profile_service=reducer-0 # Shared Storage
python auto_tester.py --app_dir=wordcount --eval_protocol=dmerge --profile_service=reducer-0 # RMMap
```



### 4. Evaluation cleanup

To cleanup all environments, you only need to remove the knative pods and `rmmod` the kernel module.

First go to `exp` and execute cleanup:

```sh
# On val05
cd $PROJECT_PATH/exp
make undeploy-meta udps
```

Then go to `as_scripts` and remove all kernel modules as:

```sh
# On val05
cd $PROJECT_PATH/ae_scripts
export PASSWORD="" # Change to your login password
python bootstrap.py -f rmmod.toml -u $USER -p $PASSWORD 
python bootstrap.py -f recover-device.toml -u $USER -p $PASSWORD 
```

