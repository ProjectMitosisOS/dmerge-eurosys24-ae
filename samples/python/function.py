import time

from bindings import *

addr = 0x4ffff5a00000

# obj = 'hello world'
obj = [3, 4]
obj.append('hello')
print(hex(id(obj)), id(obj))
print(id_deref(id(obj)))

sd = sopen()
hint = call_register(sd=sd, peak_addr=addr, hint=1)
while True:
    time.sleep(1)
