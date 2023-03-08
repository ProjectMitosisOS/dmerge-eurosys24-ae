import numpy as np
import argparse
import copy
from bindings import *

parser = argparse.ArgumentParser(
    prog='ProgramName',
    description='What the program does',
    epilog='Text at the bottom of help')
parser.add_argument('--addr', type=int, help='address of target object')
parser.add_argument('--gid', type=str, default='fe80:0000:0000:0000:ec0d:9a03:00c8:491c', help='remote mac id')
parser.add_argument('--heap_hint', type=int, default=1, help='remote heap hint')
parser.add_argument('--connect', action="store_true")  # bool

args = parser.parse_args()
addr = args.addr
gid = args.gid
heap_hint = args.heap_hint
connect = args.connect

sd = sopen()
if connect:
    res = syscall_connect_session(
        sd, gid, machine_id=0, nic_id=0)
    print("connect res %d" % res)
# obj = np.array([[1, 2, 3], [4, 5, 6]])
# print(id_deref(id(obj), type(obj)))

res = call_pull(sd=sd, hint=heap_hint, machine_id=0)
arr = id_deref(addr, None)
print(arr)
