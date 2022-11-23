import native
import time


def cur_tick():
    return int(round(time.time() * 1000_000))


if __name__ == '__main__':
    start = cur_tick()
    print(native.lib.add(4, 5))
    end = cur_tick()
    print("time consumed %d" % (end - start))
