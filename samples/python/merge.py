import argparse
import time

from bindings import *
import numpy as np

parser = argparse.ArgumentParser(
    prog='ProgramName',
    description='What the program does',
    epilog='Text at the bottom of help')
parser.add_argument('--addr', type=int, help='address of target object')
parser.add_argument('--gid', type=str, default='fe80:0000:0000:0000:ec0d:9a03:00c8:491c', help='remote mac id')
parser.add_argument('--heap_hint', type=int, default=1, help='remote heap hint')
parser.add_argument('--mac_id', type=int, default=0, help='machine ID')
parser.add_argument('--connect', action="store_true")  # bool


def cur_tick_ms():
    return int(round(time.time() * 1000))


args = parser.parse_args()
addr = args.addr
gid = args.gid
heap_hint = args.heap_hint
connect = args.connect
mac_id = args.mac_id

sd = sopen()
if connect:
    res = syscall_connect_session(
        sd, gid, machine_id=mac_id, nic_id=0)
    print("connect res %d" % res)
    assert res == 0
# obj = np.array([[1, 2, 3], [4, 5, 6]])
# print(id_deref(id(obj), type(obj)))

for i in range(10):
    tick = cur_tick_ms()
    res = call_pull(sd=sd, hint=heap_hint, machine_id=mac_id, eager_fetch=0)
    print(f'[1] finish pull {1}/ with time {cur_tick_ms() - tick}')

    data = id_deref(addr, None)
    obj = np.array(data)
    print(np.sum(obj[:][1:]))
print('done')  # FIXME: segment fault after return
