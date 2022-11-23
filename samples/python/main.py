import time

from bindings import *

addr = 0x4ffff5a00000
OFFSET = 1024 * 4
res = ccreate_heap(start_addr=addr, mem_sz=1024 * 1024)
print("get addr result: 0x%lx" % res)

print(type(res))  # of type long