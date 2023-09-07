# Dmerge

### 1. Project introduction

One set of distributed OS primitives that transparently merge (or reduce) arbitrary data structure in DAG workflow.

Submodule versions: 

- MITOSIS: [cef994](https://ipads.se.sjtu.edu.cn:1312/distributed-rdma-serverless/mitosis-project/mitosis/-/commit/cef994c32580f27f730716462dd602a95bdb9c75)
- Jemalloc: 36366f


Please check carefully before updating the submodule version

### 2. Dmerge syscall

First we clone the project and initilize the submodules as below:

```
git clone https://ipads.se.sjtu.edu.cn:1312/distributed-rdma-serverless/distributed-merge/dmerge.git
git submodule update --init --recursive
```

To compile all Rust source files, execute `make km` in the project's root directory. To load the kernel module, execute `make insmod`. You can also use `make rmmod` to unload the kernel module.

The DMerge designs two OS tier syscalls as below:

- `register_mem(id , key, vm_start, vm_end) -> vm_meta`: Resigter a dedicated (from `vm_start` to `vm_end`) memory range of the caller to the kernel. The returned `vm_meta` is an identifier of the registered memory range.
  - Implemented in [syscall_register_mem](https://ipads.se.sjtu.edu.cn:1312/distributed-rdma-serverless/distributed-merge/dmerge/-/blob/main/dmerge/src/core_syscall_handler.rs#L252)

- `rmap(mac_addr, id, key, vm_start, vm_end)-> result`: Map the dedicated (from `vm_start` to `vm_end`) at caller process.
  - Implemented in [syscall_rmap](https://ipads.se.sjtu.edu.cn:1312/distributed-rdma-serverless/distributed-merge/dmerge/-/blob/main/dmerge/src/core_syscall_handler.rs#L260)


Here’s one simple example that use these syscall to finish the DMerge.

```python
# producer side
import numpy as np
sd = sopen()
mac_addr = query_mac()
key = unique_key()
vm_start = 0x30000000
vm_end = 0x80000000
gid, mac_id, hint = register_mem(sd, key, vm_start, vm_end)
obj = np.array([1,3])
return id(obj), mac_addr, key, vm_start, vm_end

# consumer side
import numpy as np
sd = sopen()
res = rmap(sd, mac_addr, id, key, vm_start, vm_end)
obj = id_deref(obj_id)
return obj
```



### 3. Serverless workflow deployment

Before deploy all serverless function workflow, you need to deploy k8s and knative (distribued mode) on your cluster. You can refer to [knative-install](https://knative.dev/docs/install/yaml-install/) for more information. Once finished knative deployment, you can execute commands below to deploy the three function workflows (FINRA, ML training, word count):

```
cd exp/
make upapp APP_DIR=finra # For application FINRA
make upapp APP_DIR=ml-pipeline # For application ML training
make upapp APP_DIR=wordcount # For application word count
```