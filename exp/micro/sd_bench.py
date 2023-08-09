import json
import pickle
import random
import string
import sys
import time
import timeit

import lightgbm as lgb
import numpy as np
import pandas as pd
import torch


def random_np_str_arr(n):
    characters = list(string.ascii_letters + string.digits + string.punctuation)
    random.seed(1)
    length = n
    arr = np.empty(length, dtype=object)
    for i in range(length):
        random_string = ''.join(random.choices(characters, k=10))
        arr[i] = random_string
    return arr


def cur_tick_us():
    return int(round(time.time() * 1000000))


def bench_list_wrapper(inputs, bench_name, loads=pickle.loads, dumps=pickle.dumps):
    bytes_sz = 0
    obj_total_sz = 0
    s_time, d_time = 0, 0
    for input in inputs:
        tick = cur_tick_us()
        obj_bytes = dumps(input)

        s_time += (cur_tick_us() - tick) / 1000

        tick = cur_tick_us()
        obj = loads(obj_bytes)
        d_time += (cur_tick_us() - tick) / 1000

        obj_total_sz += sys.getsizeof(input)
        bytes_sz += len(obj_bytes)

    M = 1024 * 1024
    print(
        f'[<<< {bench_name}-batch {len(inputs)} >>>] bytes len {bytes_sz} .'
        f'\n\tSerialize {s_time} and Deserialize {d_time} ms'
        f'\n[Each item] obj size: {obj_total_sz / len(inputs)}, bytes size: {bytes_sz / len(inputs)}, Serialize {s_time / len(inputs)} and Deserialize {d_time / len(inputs)} ms'
    )


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


def bench_file_lines():
    path = 'data/article.txt'
    with open(path, 'r') as f:
        data = f.read()
        bench_wrapper(data, 'long str')

    with open(path, 'r') as f:
        data = f.readlines()
        bench_wrapper(data, 'list(str)')
        # bench_wrapper(tuple(data), 'tuple(str)')


def bench_np():
    file_path = 'data/Digits_Train.txt'
    data = np.genfromtxt(file_path, delimiter='\t')
    # bench_list_wrapper([10 ** 7 for i in range(5000)], 'int batch')
    # bench_list_wrapper(np.random.rand(5000).astype(float).tolist(), 'float batch')
    # bench_list_wrapper((np.random.rand(5000) + np.random.rand(5000) * 1j).tolist(), 'complex batch')
    # bench_wrapper(data.tolist(), 'list(int)')
    # bench_wrapper(tuple(data.tolist()), 'tuple(int)')
    # bench_wrapper(set(random.sample(range(10000), 5000)), 'set(int)')
    bench_wrapper(data, 'numpy.ndarray')


def bench_dataframe():
    data = pd.read_csv('data/yfinance.csv')
    bench_wrapper(data, 'pd.Dataframe')


def bench_arrow():
    import pyarrow as pa
    df_data = pd.read_csv('data/yfinance.csv')[:50]
    print(np.shape(df_data))
    file_path = 'data/Digits_Train.txt'
    T = np.genfromtxt(file_path, delimiter='\t').reshape(-1)[:80000]
    np_data = T
    li_data = pa.array(T.tolist())

    print(np.shape(np_data))

    bench_wrapper(df_data, 'arrow-dataframe')
    bench_wrapper(np_data, 'arrow-ndarray')
    bench_wrapper(li_data, 'arrow-list')

    tick = cur_tick_us()
    table = pa.Table.from_pandas(df_data)
    print(f'serialize (df -> table) time is : {(cur_tick_us() - tick) / 100} ms')

    tick = cur_tick_us()
    df = table.to_pandas()
    print(f'deserialize (table -> df) is : {(cur_tick_us() - tick) / 1000} ms')

    tick = cur_tick_us()
    array = pa.array(np_data)
    print(f'serialize (np -> arrow arr) time is : {(cur_tick_us() - tick) / 100} ms')

    tick = cur_tick_us()
    arr = array.to_numpy()
    print(f'deserialize (arrow arr -> np) is : {(cur_tick_us() - tick) / 1000} ms')

    tick = cur_tick_us()
    li_array = pa.array(li_data)
    print(f'serialize (list -> arrow) time is : {(cur_tick_us() - tick) / 100} ms')

    tick = cur_tick_us()
    d = li_array.to_pylist()
    print(f'deserialize (arrow -> list) is : {(cur_tick_us() - tick) / 1000} ms')


def bench_lgbm():
    model_path = 'data/mnist_model.txt'
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
            t = random.randint(1, 10)
            if t % 2 == 0:
                return random.randint(1, 10000)
            else:
                return ''.join(random.choice(ascii_lowercase) for _ in range(20))
        else:
            d = {}
            for i in range(breadth):
                key = ''.join(random.choice(ascii_lowercase) for _ in range(20))
                value = random_dict(depth - 1, breadth)
                d[key] = value
            return d

    data = random_dict(depth=6, breadth=6)
    bench_wrapper(data, 'complex dict')


def bench_pil_img():
    from PIL import Image
    img = Image.open('data/img.jpg')
    bench_wrapper(img, 'PIL.Image')


if __name__ == '__main__':
    # file_path = 'data/Digits_Train.txt'
    # data = np.genfromtxt(file_path, delimiter='\t')
    # bench_map()
    # bench_dataframe()
    # bench_file_lines()
    # bench_lgbm()
    # bench_pil_img()
    bench_arrow()
