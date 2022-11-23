from bindings import *

res = ccreate_heap(start_addr=0x4ffff5a00000, mem_sz=1024)
sd = sopen()
res = syscall_connect_session(
    sd,
    "fe80:0000:0000:0000:ec0d:9a03:00c8:491c", 0, 0)
print(res)
