import numpy as np
import time
import copy
from bindings import *

obj = range(3)
addr = 0x4ffff5a00000
# obj = 'hello world'

obj = {
    'li': [3, 4, 5],
    'str': 'hello world',
    'range': range(30),
}
# obj = np.array([[1, 2, 3], [444, 5, 6]])

new_obj = copy.heapsize(obj)
print('obj id:', id(obj), type(obj))
print(id_deref(id(obj), type(obj)))
sd = sopen()
hint = call_register(sd=sd, peak_addr=addr, hint=1)
while True:
    time.sleep(1)
