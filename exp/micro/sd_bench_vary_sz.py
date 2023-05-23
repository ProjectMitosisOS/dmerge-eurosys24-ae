import random
import sys

import numpy as np
import pandas as pd
import pickle
import time


def cur_tick_us():
    return int(round(time.time() * 1000000))


byte_sz = [1024, 512 * 1024, 1024 * 1024, 2 * 1024 * 1024,
           4 * 1024 * 1024, 8 * 1024 * 1024, 16 * 1024 * 1024, 32 * 1024 * 1024,
           64 * 1024 * 1024, 128 * 1024 * 1024, 256 * 1024 * 1024,
           512 * 1024 * 1024, 1024 * 1024 * 1024]


def bench_wrapper(input, bench_name, loads=pickle.loads, dumps=pickle.dumps):
    tick = cur_tick_us()

    obj_bytes = dumps(input)

    s_time = (cur_tick_us() - tick) / 1000

    tick = cur_tick_us()
    obj = loads(obj_bytes)
    d_time = (cur_tick_us() - tick) / 1000

    obj_sz = sys.getsizeof(input)
    bytes_sz = len(obj_bytes)
    M = 1024 * 1024
    print(
        f'[<<< {bench_name} >>>] with object size {obj_sz} ({obj_sz / M} M), bytes len {bytes_sz} ({bytes_sz / M} M).'
        f'\n\tSerialize {s_time} and Deserialize {d_time} ms')


def test_vary_sz(df, size):
    tick = cur_tick_us()
    d_time = (cur_tick_us() - tick) / 1000
    print(
        f'[<<< {"obj-" + str(size)} >>>] Heapize time {d_time} ms')
    bench_wrapper(df, "obj-" + str(size))


for bytes in byte_sz:
    available_bytes = int(bytes / 2)

    obj = np.random.randint(0, 100, size=available_bytes).tolist()
    test_vary_sz(obj, bytes)
