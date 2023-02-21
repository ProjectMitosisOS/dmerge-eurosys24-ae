import time
from bindings import *

obj = range(3)
addr = 0x4ffff5a00000
# obj = 'hello world'
print(hex(id(obj)), id(obj))
print(id_deref(id(obj)))

sd = sopen()
hint = call_register(sd=sd, peak_addr=addr, hint=1)
while True:
    time.sleep(1)
