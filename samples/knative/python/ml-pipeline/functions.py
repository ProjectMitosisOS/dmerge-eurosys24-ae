import redis_client
from redis_client import *

test_data_file_path = 'dataset/Digits_Test.txt'
train_data_file_path = 'dataset/Digits_Train.txt'

# Dump before running
dump_file_to_kv(train_data_file_path)
dump_file_to_kv(test_data_file_path)


def splitter(meta):
    out_data = meta.copy()

    content = read_file_from_kv(train_data_file_path)
    redis_client.put(train_data_file_path, len(content))

    out_data['key'] = train_data_file_path
    return out_data


def trainer(meta):
    out_data = meta.copy()

    data = redis_client.get(meta['key'])
    out_data['len-of-content'] = data

    return out_data


def reduce(meta):
    out_data = meta.copy()
    return out_data
