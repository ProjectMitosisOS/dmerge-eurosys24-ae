import os
import time

import util
from util import cur_tick_ms, cur_tick_us
from bindings import *

sd = sopen()

addr = int(os.environ.get('BASE_HEX'), 16)
tick = cur_tick_us()
gid, mac_id, hint = util.push(sd=sd, nic_id=0, peak_addr=addr)
push_time = (cur_tick_us() - tick) / 1000
print(f'push time: {push_time} ms')

for i in range(5):
    time.sleep(1)
    # print('waiting...')
