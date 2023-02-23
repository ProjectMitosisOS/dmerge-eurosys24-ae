import numpy as np
import argparse
import copy
from bindings import *

parser = argparse.ArgumentParser(
    prog='ProgramName',
    description='What the program does',
    epilog='Text at the bottom of help')
parser.add_argument('--addr', type=int, help='address of target object')
parser.add_argument('--mac_id', type=str, default='fe80:0000:0000:0000:ec0d:9a03:0078:647e', help='remote mac id')
args = parser.parse_args()
addr = args.addr
mac_id = args.mac_id

print("id: ", hex(addr))
sd = sopen()
res = syscall_connect_session(
    sd, mac_id, 0, 0)
print("connect res %d" % res)
# obj = np.array([[1, 2, 3], [4, 5, 6]])
# print(id_deref(id(obj), type(obj)))

res = call_pull(sd=sd, hint=1, machine_id=0)
arr = id_deref(addr, np.ndarray)
print(arr)
