import os
import uuid

import numpy as np
from bindings import *
from flask import current_app
from minio import Minio
import lightgbm as lgb
import util
from util import cur_tick_ms
import math
import re

global_obj = {}

s3_client = Minio(
    endpoint='minio:9000',
    secure=False,
    access_key='ACCESS_KEY', secret_key='SECRET_KEY')
bucket_name = 'word-count'
if not s3_client.bucket_exists(bucket_name):
    s3_client.make_bucket(bucket_name)


# Profile is seperated into 4 parts as below:
# @Execution: Normal data process
# @Interaction with external resources: Current is Redis KV
# @Serialize: Data transform into IR
# @Deserialize: IR transform into Data

def read_lines(path):
    with open(path) as f:
        return f.readlines()


def accuracy_score(y_true, y_pred):
    correct = 0
    for i in range(len(y_true)):
        if y_true[i] == y_pred[i]:
            correct += 1
    accuracy = correct / len(y_true)
    return accuracy


def fill_gid(gid):
    new_mac_id_parts = []
    for part in gid.split(":"):
        new_part = ":".join([str(hex(int(i, 16)))[2:].zfill(4) for i in part.split(".")])
        new_mac_id_parts.append(new_part)
    new_mac_id = ":".join(new_mac_id_parts)
    return new_mac_id


def splitter(meta):
    text_path = 'datasets/OliverTwist_CharlesDickens/OliverTwist_CharlesDickens_English.txt'
    s3_object_key = 'article'

    def execute_body(path, mapper_num=3):
        with open(path) as f:
            lines = f.readlines()
        total_lines = len(lines)
        lines_per_file = math.ceil(total_lines / mapper_num)
        wcs = []
        for i in range(mapper_num):
            start = i * lines_per_file
            end = min((i + 1) * lines_per_file, total_lines)
            wcs.append(lines[start:end])
        return wcs

    mapper_num = int(os.environ.get('MAPPER_NUM', 3))
    wcs = execute_body(text_path, mapper_num=mapper_num)
    wf_start_tick = cur_tick_ms()
    out_meta = {
        'statusCode': 200,
        'wf_id': str(uuid.uuid4()),
        'mapper_num': mapper_num,
        'profile': {
            'wf_start_tick': wf_start_tick
        },
        's3_obj_key': s3_object_key,
        'data': wcs
    }
    # s3_client.fput_object(bucket_name, s3_object_key, text_path)
    return out_meta


def mapper(meta):
    ID = int(os.environ.get('ID', 0))

    def execute_body(lines):
        word_count = {}
        for line in lines:
            words = re.findall(r'\w+', line.lower())
            for word in words:
                if word not in word_count:
                    word_count[word] = 1
                else:
                    word_count[word] += 1
        return word_count

    self_data = meta['data'][ID]
    wc_res = execute_body(self_data)
    meta['data'] = wc_res
    return meta


def reducer(metas):
    def execute_body(word_counts):
        word_count = {}
        for wc in word_counts:
            for word, count in wc.items():
                if word not in word_count:
                    word_count[word] = count
                else:
                    word_count[word] += count
        return word_count

    wc_aggregate = [event['data'] for event in metas]
    wc_res = execute_body(wc_aggregate)
    T = cur_tick_ms() - metas[-1]["profile"]["wf_start_tick"]
    current_app.logger.info(f'workflow passed {T} ms')
    return {}


def default_handler(meta):
    current_app.logger.info(f'not a default path for type')
    return meta
