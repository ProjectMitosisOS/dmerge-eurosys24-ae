import numpy as np
import time
import copy
from bindings import *
import os

obj = range(3)
addr = int(os.environ.get('BASE_HEX'), 16)


def fill_gid(mac_id):
    new_mac_id_parts = []
    for part in mac_id.split(":"):
        new_part = ":".join([str(hex(int(i, 16)))[2:].zfill(4) for i in part.split(".")])
        new_mac_id_parts.append(new_part)
    new_mac_id = ":".join(new_mac_id_parts)
    return new_mac_id


obj = {
    'li': [3, 4, 5, 7],
    'str': 'hello world',
    'range': range(30),
}

print('obj id:', id(obj), type(obj))
print(id_deref(id(obj), type(obj)))
sd = sopen()
mac_id = fill_gid(syscall_get_gid(sd=sd, nic_idx=0))

hint = call_register(sd=sd, peak_addr=addr)
print(f'gid is {mac_id} , addr is {id(obj)} ,hint is {hint}')
while True:
    time.sleep(1)
