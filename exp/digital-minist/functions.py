import os
import uuid

import numpy as np
from bindings import *
from flask import current_app
from minio import Minio

import util
from util import cur_tick_ms

global_obj = {}

s3_client = Minio(
    endpoint='minio:9000',
    secure=False,
    access_key='ACCESS_KEY', secret_key='SECRET_KEY')
bucket_name = 'digital-minist'
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


def fill_gid(gid):
    new_mac_id_parts = []
    for part in gid.split(":"):
        new_part = ":".join([str(hex(int(i, 16)))[2:].zfill(4) for i in part.split(".")])
        new_mac_id_parts.append(new_part)
    new_mac_id = ":".join(new_mac_id_parts)
    return new_mac_id


def splitter(meta):
    wf_start_tick = cur_tick_ms()

    tick = cur_tick_ms()
    predict_worker_num = int(os.environ.get('WORKER_NUM', '1'))
    test_data = np.genfromtxt('dataset/Digits_Test.txt', delimiter='\t')
    split_arr = np.array_split(test_data, predict_worker_num)
    execute_time = cur_tick_ms() - tick
    protocol = util.PROTOCOL
    meta['profile'] = {}

    def splitter_s3(meta, split_arr):
        s3_time = 0
        sd_time = 0
        store_path = '/tmp/test_data_'
        out_dict = dict(meta)
        out_dict['s3_obj_key'] = {}
        for i, data in enumerate(split_arr):
            tick = cur_tick_ms()
            path = store_path + str(i)
            obj_key = 'digit_' + str(i)
            np.savetxt(path, data, delimiter='\t')
            sd_time += cur_tick_ms() - tick

            tick = cur_tick_ms()
            s3_client.fput_object(bucket_name, obj_key, path)
            out_dict['s3_obj_key'][str(i)] = obj_key
            s3_time += cur_tick_ms() - tick
        out_dict['profile']['splitter'] = {
            's3_time': s3_time,
            'sd_time': sd_time,
        }
        return out_dict

    def splitter_dmerge(meta, split_arr):
        global_obj['train_data'] = {}
        out_dict = dict(meta)
        out_dict['obj_hash'] = {}
        push_time = 0
        addr = int(os.environ.get('BASE_HEX', '100000000'), 16)
        push_start_time = cur_tick_ms()
        nic_idx = 0
        for i, data in enumerate(split_arr):
            data_li = data.tolist()
            global_obj[str(i)] = data_li
            out_dict['obj_hash'][str(i)] = id(global_obj[str(i)])

        gid, mac_id, hint = util.push(nic_id=nic_idx, peak_addr=addr)
        push_time += cur_tick_ms() - push_start_time
        out_dict['route'] = {
            'gid': gid,
            'machine_id': mac_id,
            'nic_id': nic_idx,
            'hint': hint
        }
        out_dict['profile'].update({
            'splitter': {
                'push_time': push_time,
            },
            'leave_tick': cur_tick_ms()
        })
        return out_dict

    predict_dispatcher = {
        'S3': splitter_s3,
        'DMERGE': splitter_dmerge,
        'P2P': splitter_s3
    }
    dispatch_key = protocol
    out_dict = predict_dispatcher[dispatch_key](meta, split_arr)
    out_dict.update({
        'wf_id': str(uuid.uuid4()),
        'features': {'protocol': protocol},
    })
    out_dict['profile']['leave_tick'] = cur_tick_ms()
    out_dict['profile']['wf_start_tick'] = wf_start_tick
    out_dict['profile']['splitter']['execute_time'] = execute_time
    out_dict['profile']['splitter']['stage_time'] = sum(out_dict['profile']['splitter'].values())
    return out_dict


def predict(meta):
    start_tick = cur_tick_ms()

    def execute_body(data):
        y_test = data[:, 0]
        x_test = data[:, 1:data.shape[1]]
        np.savetxt("/tmp/target.txt", data, delimiter='\t')
        return []

    def predict_s3(_meta):
        current_app.logger.info(f"meta in predict s3: {_meta}")
        out_dict = dict(_meta)
        tick = cur_tick_ms()
        ID = os.environ.get('ID', 0)
        path = '/tmp/digits_' + str(ID) + '.txt'
        s3_obj = _meta['s3_obj_key'][str(ID)]
        s3_client.fget_object(bucket_name, s3_obj, path)  # download all
        s3_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        data = np.genfromtxt(path, delimiter='\t')
        sd_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        score = execute_body(data)
        execute_time = cur_tick_ms() - tick

        out_dict['score'] = score
        out_dict['profile'].update({
            'predict': {
                'execute_time': execute_time,
                's3_time': s3_time,
                'sd_time': sd_time,
                'nt_time': start_tick - _meta['profile']['leave_tick']
            }
        })
        return out_dict

    def predict_dmerge(_meta):
        out_dict = dict(_meta)

        tick = cur_tick_ms()
        ID = os.environ.get('ID', 0)
        route = _meta['route']
        gid, mac_id, hint, nic_id = route['gid'], route['machine_id'], \
            route['hint'], route['nic_id']
        util.pull(mac_id, hint)
        data = util.fetch(meta['obj_hash'][str(ID)])
        pull_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        test_data = np.array(data)
        score = execute_body(test_data)
        execute_time = cur_tick_ms() - tick

        out_dict['score'] = score
        out_dict['profile'].update({
            'predict': {
                'execute_time': execute_time,
                'pull_time': pull_time,
                'nt_time': start_tick - _meta['profile']['leave_tick']
            }
        })
        return out_dict

    predict_dispatcher = {
        'S3': predict_s3,
        'DMERGE': predict_dmerge,
        'P2P': predict_s3
    }
    dispatch_key = meta['features']['protocol']
    out_dict = predict_dispatcher[dispatch_key](meta)
    out_dict['profile']['leave_tick'] = cur_tick_ms()
    out_dict['profile']['predict']['stage_time'] = sum(out_dict['profile']['predict'].values())
    return out_dict


def combine(metas):
    tick = cur_tick_ms()
    for i, event in enumerate(metas):
        event['profile']['wf_e2e_time'] = tick - event['profile']['wf_start_tick']
        current_app.logger.info(f"event@{i} profile: {event['profile']}")
    return {}


def default_handler(meta):
    current_app.logger.info(f'not a default path for type')
    return meta


if __name__ == '__main__':
    res = predict({})
