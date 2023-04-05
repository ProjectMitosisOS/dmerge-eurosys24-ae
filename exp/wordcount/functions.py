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
import pickle

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
    text_path = 'datasets/OliverTwist_CharlesDickens/OliverTwist_CharlesDickens_French.txt'
    stage_name = 'splitter'
    wf_start_tick = cur_tick_ms()

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

    def splitter_rrpc(meta, mapper_num):
        tick = cur_tick_ms()
        wcs = execute_body(text_path, mapper_num=mapper_num)
        execute_time = cur_tick_ms() - tick
        out_meta = {
            'data': wcs,
            'profile': {
                stage_name: {
                    'execute_time': execute_time
                }
            },
        }
        return out_meta

    def splitter_s3(meta, mapper_num):
        tick = cur_tick_ms()
        wcs = execute_body(text_path, mapper_num=mapper_num)
        execute_time = cur_tick_ms() - tick

        out_file_path = text_path + '.txt'

        tick = cur_tick_ms()
        with open(out_file_path, 'wb') as f:
            pickle.dump(wcs, f)
        sd_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        s3_client.fput_object(bucket_name, out_file_path, out_file_path)
        s3_time = cur_tick_ms() - tick

        out_meta = {
            's3_obj_key': out_file_path,
            'profile': {
                stage_name: {
                    'execute_time': execute_time,
                    'sd_time': sd_time,
                    's3_time': s3_time,
                }
            },
        }
        return out_meta

    splitter_dispatcher = {
        'S3': splitter_s3,
        'RRPC': splitter_rrpc,
        'DMERGE': splitter_rrpc,
        'DMERGE_PUSH': splitter_rrpc,
    }
    mapper_num = int(os.environ.get('MAPPER_NUM', 3))
    dispatch_key = util.PROTOCOL
    return_dict = splitter_dispatcher[dispatch_key](meta, mapper_num)

    return_dict.update({
        'statusCode': 200,
        'wf_id': str(uuid.uuid4()),
    })

    return_dict['profile']['wf_start_tick'] = wf_start_tick
    return_dict['profile']['leave_tick'] = cur_tick_ms()
    return_dict['profile'][stage_name]['stage_time'] = \
        sum(return_dict['profile'][stage_name].values())
    return return_dict


def mapper(meta):
    stage_name = 'mapper'
    stage_start_tick = cur_tick_ms()

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

    def mapper_s3(meta):
        ID = int(os.environ.get('ID', 0))
        s3_obj_key = meta['s3_obj_key']
        file_path = '/tmp/article.txt'
        tick = cur_tick_ms()
        s3_client.fget_object(bucket_name, s3_obj_key, file_path)
        s3_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        with open(file_path, 'rb') as f:
            lines = pickle.load(f)[ID]
        sd_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        wc_res = execute_body(lines)
        execute_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        out_file_path = '/tmp/wc.txt'
        with open(out_file_path, 'wb') as f:
            pickle.dump(wc_res, f)
        sd_time += cur_tick_ms() - tick

        tick = cur_tick_ms()
        s3_client.fput_object(bucket_name, out_file_path, out_file_path)
        s3_time += cur_tick_ms() - tick

        meta['s3_obj_key'] = out_file_path
        meta['profile'][stage_name] = {
            'execute_time': execute_time,
            's3_time': s3_time,
            'sd_time': sd_time,
            'nt_time': stage_start_tick - meta['profile']['leave_tick']
        }
        return meta

    def mapper_rrpc(meta):
        ID = int(os.environ.get('ID', 0))
        tick = cur_tick_ms()
        self_data = meta['data'][ID]
        wc_res = execute_body(self_data)
        execute_time = cur_tick_ms() - tick
        meta['data'] = wc_res
        meta['profile'][stage_name] = {
            'execute_time': execute_time,
            'nt_time': stage_start_tick - meta['profile']['leave_tick']
        }
        return meta

    mapper_dispatcher = {
        'S3': mapper_s3,
        'RRPC': mapper_rrpc,
        'DMERGE': mapper_rrpc,
        'DMERGE_PUSH': mapper_rrpc,
    }
    dispatch_key = util.PROTOCOL
    return_dict = mapper_dispatcher[dispatch_key](meta)
    return_dict['profile']['leave_tick'] = cur_tick_ms()
    return_dict['profile'][stage_name]['stage_time'] = \
        sum(return_dict['profile'][stage_name].values())
    return meta


def reducer(metas):
    stage_name = 'reducer'
    stage_start_tick = cur_tick_ms()

    def execute_body(word_counts):
        word_count = {}
        for wc in word_counts:
            for word, count in wc.items():
                if word not in word_count:
                    word_count[word] = count
                else:
                    word_count[word] += count
        return word_count

    def reducer_s3(metas):
        datas = []
        ce = metas[-1]
        s3_time = 0
        sd_time = 0

        for event in metas:
            tick = cur_tick_ms()
            s3_obj_key = event['s3_obj_key']
            s3_client.fget_object(bucket_name, s3_obj_key, s3_obj_key)
            s3_time += cur_tick_ms() - tick

            tick = cur_tick_ms()
            with open(s3_obj_key, 'rb') as f:
                wc = pickle.load(f)
                datas.append(wc)
            sd_time += cur_tick_ms() - tick

        tick = cur_tick_ms()
        wc_res = execute_body(datas)
        execute_time = cur_tick_ms() - tick

        ce['profile'][stage_name] = {
            'execute_time': execute_time,
            's3_time': s3_time,
            'sd_time': sd_time,
            'nt_time': stage_start_tick - ce['profile']['leave_tick']
        }
        return ce

    def reducer_rrpc(metas):
        tick = cur_tick_ms()
        wc_aggregate = [event['data'] for event in metas]
        wc_res = execute_body(wc_aggregate)
        execute_time = cur_tick_ms() - tick

        event = metas[-1]
        event['profile'][stage_name] = {
            'execute_time': execute_time,
            'nt_time': stage_start_tick - event['profile']['leave_tick']
        }
        return event

    reducer_dispatcher = {
        'S3': reducer_s3,
        'RRPC': reducer_rrpc,
        'DMERGE': reducer_rrpc,
        'DMERGE_PUSH': reducer_rrpc,
    }
    dispatch_key = util.PROTOCOL
    return_dict = reducer_dispatcher[dispatch_key](metas)
    return_dict['profile'][stage_name]['stage_time'] = \
        sum(return_dict['profile'][stage_name].values())

    T = cur_tick_ms() - metas[-1]["profile"]["wf_start_tick"]
    p = return_dict['profile']
    current_app.logger.info(f'return profile {p}')
    current_app.logger.info(f'workflow passed {T} ms')
    reduced_profile = util.reduce_profile(p)
    for k, v in reduced_profile.items():
        current_app.logger.info(f"Part@ {k} passed {v} ms")
    return {}


def default_handler(meta):
    current_app.logger.info(f'not a default path for type')
    return meta
