import copy
import numpy as np
import uuid
import os
from util import cur_tick_ms
from numpy.linalg import eig
from bindings import *

addr = int(os.environ.get('BASE_HEX', '100000000'), 16)
sd = sopen()
gid, mac_id = syscall_get_gid(sd=sd, nic_idx=0)
gid = fill_gid(gid)
# hint = call_register(sd=sd, peak_addr=addr)

print(f'gid is {gid} ,'
      f'ObjectID is {id(addr)} ,'
      f'hint is {1} ,'
      f'mac id {mac_id} ,'
      f'addr in {hex(addr)}')
