import pickle

import numpy as np

import time
import json


def cur_tick_ms():
    return int(round(time.time() * 1000))


data = np.genfromtxt('data/digits.txt', delimiter='\t')

tick = cur_tick_ms()

s = pickle.dumps(data)
print(f'pickle seri\t {cur_tick_ms() - tick}')

tick = cur_tick_ms()
res = pickle.loads(s)
print(f'pickle deseri\t{cur_tick_ms() - tick}')

file_path = 'tmp.s'
tick = cur_tick_ms()
with open(file_path, 'wb') as f:
    pickle.dump(data, f)
print(f'pickle seri to File\t{cur_tick_ms() - tick}')

tick = cur_tick_ms()
with open(file_path, 'rb') as f:
    d = pickle.load(f)
print(f'pickle deseri to File\t{cur_tick_ms() - tick}')

tick = cur_tick_ms()
s = json.dumps(data.tolist())
print(f'json seri\t {cur_tick_ms() - tick}')

tick = cur_tick_ms()
res = np.array(json.loads(s))
print(f'json deseri\t{cur_tick_ms() - tick}')

file_path = 'digit.txt'
tick = cur_tick_ms()
np.save('digit.txt', data)
print(f'put numpy arr\t{cur_tick_ms() - tick}')

tick = cur_tick_ms()
data_s = np.load(file_path + '.npy')
print(f'get numpy arr\t{cur_tick_ms() - tick}')
