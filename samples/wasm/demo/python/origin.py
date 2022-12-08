import time
start = time.time() * 1000000
for i in range(50000):
    num = i * i

end = time.time() * 1000000
print('passed %d us' % (end - start))