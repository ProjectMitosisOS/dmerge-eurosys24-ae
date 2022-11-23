from bindings import *

addr = 0x4ffff5a00000

ccreate_heap(start_addr=addr, mem_sz=1024 * 1024)
sd = sopen()
hint = call_register(sd=sd, peak_addr=addr, hint=1)
