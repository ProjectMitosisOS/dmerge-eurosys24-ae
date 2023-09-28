import numpy as np
import time
import copy
from bindings import *
import os

obj = range(3)
addr = int(os.environ.get('BASE_HEX', '300000'), 16)


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

print('obj id:', id(obj), type(obj), 'hex id', hex(id(obj)))
print(id_deref(id(obj), type(obj)))
sd = sopen()
gid, mac_id = syscall_get_gid(sd=sd, nic_idx=0)
# hint = call_register(sd=sd, peak_addr=addr)
print(f'gid is {gid} , addr is {id(obj)} ,hint is {3}, mac id {mac_id}')
