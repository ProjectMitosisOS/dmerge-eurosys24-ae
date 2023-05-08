import pickle

import numpy as np
import sys
import time
import lightgbm as lgb
import pandas as pd
import torch


def cur_tick_ms():
    return int(round(time.time() * 1000))


def bench_wrapper(input, bench_name):
    tick = cur_tick_ms()

    obj_bytes = pickle.dumps(input)

    s_time = cur_tick_ms() - tick

    tick = cur_tick_ms()
    obj = pickle.loads(obj_bytes)
    d_time = cur_tick_ms() - tick

    obj_sz = sys.getsizeof(input)
    bytes_sz = len(obj_bytes)
    M = 1024 * 1024
    print(
        f'[<<< {bench_name} >>>] with object size {obj_sz} ({obj_sz / M} M), bytes len {bytes_sz} ({bytes_sz / M} M).'
        f'\n\tSerialize {s_time} and Deserialize {d_time} ms')


def bench_file_lines():
    with open('data/article.txt', 'r') as f:
        data = f.readlines()
        bench_wrapper(data, 'article `readlines()`')

    with open('data/article.txt', 'rb') as f:
        data = f.read()
        bench_wrapper(data, 'article `read()`')


def bench_np():
    file_path = 'data/Digits_Train.txt'
    data = np.genfromtxt(file_path, delimiter='\t')
    with open(file_path, 'r') as f:
        d = f.readlines()
        bench_wrapper(d, 'numpy file `readlines()`')

    with open(file_path, 'rb') as f:
        d = f.read()
        bench_wrapper(d, 'numpy file `read()`')
    bench_wrapper(data, 'numpy.ndarray')
    bench_wrapper(data.tolist(), 'builtin int array')


def bench_dataframe():
    data = pd.read_csv('data/yfinance.csv')
    bench_wrapper(data, 'Dataframe')

    bench_wrapper(data.to_numpy(), 'Dataframe->to_numpy()')
    bench_wrapper(data.to_numpy().tolist(), 'Dataframe->to_numpy()->tolist()')


def bench_lgbm():
    data = lgb.Booster(model_file='data/mnist_model.txt')
    bench_wrapper(data, 'lgb tree')


def bench_nn():
    data = torch.load('data/mnist_net.pth')
    bench_wrapper(data, 'torch nn')


def bench_map():
    def random_dict(depth=2, breadth=2):
        """
        Generate a random complex dict
        :param depth: Max depth of the dict
        :param breadth: KV pair number for each layer of the dict
        :return:
        """
        import random
        from string import ascii_lowercase
        if depth == 0:
            return random.randint(1, 10000)
        else:
            d = {}
            for i in range(breadth):
                key = ''.join(random.choice(ascii_lowercase) for _ in range(20))
                value = random_dict(depth - 1, breadth)
                d[key] = value
            return d

    data = random_dict(depth=6, breadth=6)
    bench_wrapper(data, 'complex dict')


if __name__ == '__main__':
    bench_file_lines()
    bench_np()
    bench_dataframe()
    bench_lgbm()
    bench_nn()
    bench_map()
