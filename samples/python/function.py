import os
import time
import numpy as np
from bindings import *

obj = range(3)
addr = int(os.environ.get('BASE_HEX'), 16)


def fill_gid(mac_id):
    new_mac_id_parts = []
    for part in mac_id.split(":"):
        new_part = ":".join([str(hex(int(i, 16)))[2:].zfill(4) for i in part.split(".")])
        new_mac_id_parts.append(new_part)
    new_mac_id = ":".join(new_mac_id_parts)
    return new_mac_id


li = np.genfromtxt('Digits_Train.txt', delimiter='\t')

obj = li.tolist()


def push(sd, nic_id, peak_addr):
    gid, mac_id = syscall_get_gid(sd=sd, nic_idx=nic_id)
    gid = fill_gid(gid)
    hint = call_register(sd=sd, peak_addr=peak_addr)
    return gid, mac_id, hint


print('obj id:', id(obj), type(obj))
sd = sopen()
gid, mac_id, hint = push(sd, nic_id=0, peak_addr=addr)
gid = fill_gid(gid)
print(f'gid is {gid} , addr is {id(obj)} ,hint is {hint}')
print(np.sum(obj[:][1:]))

while True:
    time.sleep(1)
    # print('waiting...')
