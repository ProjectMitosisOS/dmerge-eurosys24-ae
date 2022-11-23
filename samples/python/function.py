import time

from bindings import *

addr = 0x4ffff5a00000
OFFSET = 1024 * 4
res = ccreate_heap(start_addr=addr, mem_sz=1024 * 1024)
my_write_ptr(addr=addr + OFFSET, val=124125)
print(my_read_ptr(addr + OFFSET))

sd = sopen()
hint = call_register(sd=sd, peak_addr=addr, hint=1)

while True:
    time.sleep(1)
