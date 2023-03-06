import numpy as np
import time
import copy
from bindings import *

obj = range(3)
addr = 0x4ffff5a00000


def fill_mac_id(mac_id):
    new_mac_id_parts = []
    for part in mac_id.split(":"):
        new_part = ":".join([str(hex(int(i, 16)))[2:].zfill(4) for i in part.split(".")])
        new_mac_id_parts.append(new_part)
    new_mac_id = ":".join(new_mac_id_parts)
    return new_mac_id


obj = {
    'li': [3, 4, 5],
    'str': 'hello world',
    'range': range(30),
}

print('obj id:', id(obj), type(obj))
print(id_deref(id(obj), type(obj)))
sd = sopen()
mac_id = fill_mac_id(syscall_get_mac_id(sd=sd, nic_idx=0))
print(f'mac id is {mac_id}, addr is {id(obj)}')

hint = call_register(sd=sd, peak_addr=addr, hint=1)
while True:
    time.sleep(1)
