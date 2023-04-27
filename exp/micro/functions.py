import json
import os
import pickle
import uuid

from bindings import *
from flask import current_app
from minio import Minio

from util import cur_tick_ms
import util

s3_client = Minio(
    endpoint='minio:9000',
    secure=False,
    access_key='ACCESS_KEY', secret_key='SECRET_KEY')
bucket_name = 'micro'
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
    data_path = 'data/digits.txt'
    s3_client.fput_object(bucket_name, 'digits', data_path)
    return {
        'status': 200,
        's3_obj_key': 'digits',
        'wf_id': str(uuid.uuid4()),
        'features': {
            'protocol': os.environ.get('PROTOCOL', 'S3')  # value of DMERGE / S3 / RPC --- Default as S3
        },
        'profile': {
            'leave_tick': cur_tick_ms(),
            'runtime': {
                'fetch_data_time': 0,
                'nt_time': 0,
            }
        },

    }


import numpy as np

global_obj = {}


def producer(meta):
    def execute_body():
        k = 1  # TODO: replace k
        arr = np.genfromtxt(local_data_path, delimiter='\t')
        sub_arrays = np.array_split(arr, k)
        return sub_arrays[0]

    stage_name = 'producer'
    s3_obj = meta['s3_obj_key']
    local_data_path = '/tmp/digits.txt'
    s3_client.fget_object(bucket_name, s3_obj, local_data_path)  # download all
    out_data = execute_body()

    def producer_s3(_meta):
        filename = "/tmp/data.txt"
        out_meta = _meta
        tick = cur_tick_ms()
        with open(filename, 'w') as f:
            json.dump(out_data.tolist(), f)
        sd_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        s3_obj_key = 'Data.txt'
        s3_client.fput_object(bucket_name, s3_obj_key, filename)
        s3_time = cur_tick_ms() - tick

        out_meta['s3_obj_key'] = s3_obj_key
        out_meta['profile'].update({
            'producer': {
                's3_time': s3_time,
                'sd_time': sd_time,
            },
        })
        return out_meta

    def producer_rpc(_meta):
        out_meta = _meta

        tick = cur_tick_ms()
        out_meta['payload'] = out_data.tolist()
        # pickle.dumps(out_meta)
        sd_time = cur_tick_ms() - tick

        out_meta['profile'].update({
            'producer': {
                'sd_time': sd_time,
            },
        })
        return out_meta

    def producer_dmerge(_meta):
        out_meta = _meta

        li = out_data.tolist()
        tick = cur_tick_ms()
        global_obj['data'] = li  # write to global variable to avoid GC

        addr = int(os.environ.get('BASE_HEX', '100000000'), 16)
        execute_time = cur_tick_ms() - tick

        push_start_time = cur_tick_ms()
        sd = sopen()
        nic_idx = 0
        gid, mac_id = syscall_get_gid(sd=sd, nic_idx=nic_idx)
        gid = fill_gid(gid)
        hint = call_register(sd=sd, peak_addr=addr)
        push_time = cur_tick_ms() - push_start_time

        obj_id = id(global_obj["data"])

        out_meta.pop('s3_obj_key')
        out_meta['profile'].update({
            'producer': {
                'push_time': push_time,
                'execute_time': execute_time,
            },
        })
        out_meta['obj_hash'] = {
            'data': obj_id
        }
        out_meta['route'] = {
            'gid': gid,
            'machine_id': mac_id,
            'nic_id': nic_idx,
            'hint': hint
        }
        current_app.logger.debug(f'DMERGE profile: {out_meta["profile"]}')
        return out_meta

    wf_start_tick = cur_tick_ms()
    producer_dispatcher = {
        'S3': producer_s3,
        'DMERGE': producer_dmerge,
        'RPC': producer_rpc
    }
    dispatch_key = meta['features']['protocol']
    out_dict = producer_dispatcher[dispatch_key](meta)
    out_dict['profile']['leave_tick'] = cur_tick_ms()
    out_dict['profile']['wf_start_tick'] = wf_start_tick
    out_dict['profile'][stage_name]['stage_time'] = sum(out_dict['profile'][stage_name].values())
    return out_dict


def consumer(event):
    stage_name = 'consumer'

    def consumer_s3(event):
        out_meta = event

        s3_obj_key = event['s3_obj_key']

        tick = cur_tick_ms()
        local_data_path = '/tmp/digits.txt'
        s3_client.fget_object(bucket_name, s3_obj_key, local_data_path)
        s3_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        with open(local_data_path, 'rb') as f:
            data = np.array(json.load(f))
            # data = pickle.load(f)
        sd_time = cur_tick_ms() - tick

        out_meta['profile'].update({
            'consumer': {
                's3_time': s3_time,
                'sd_time': sd_time,
            },
        })
        current_app.logger.debug(f'S3 profile: {out_meta["profile"]}')
        return out_meta

    def consumer_rpc(_event):
        tick = cur_tick_ms()
        d = np.array(event['payload'])
        sd_time = cur_tick_ms() - tick

        event.pop('payload')
        out_meta = event
        out_meta['profile'].update({
            'consumer': {
                'sd_time': sd_time,
            },
        })
        current_app.logger.debug(f'S3 profile: {out_meta["profile"]}')
        return out_meta

    def consumer_dmerge(event):
        out_meta = event
        target_id = event['obj_hash']['data']
        route = event['route']
        gid, mac_id, hint, nic_id = route['gid'], route['machine_id'], \
            route['hint'], route['nic_id']

        pull_start_time = cur_tick_ms()
        sd = sopen()
        current_app.logger.debug(f"connect res {0}. gid: {gid} ,"
                                 f"machine id {mac_id} ,"
                                 f"hint {hint} ,"
                                 f"nic id {nic_id}")
        res = call_pull(sd=sd, hint=hint, machine_id=mac_id, eager_fetch=0)
        obj = np.array(id_deref(target_id, None)) # Retrieve all or not
        # current_app.logger.debug(f'get result. arr len {np.shape(obj)}')
        pull_time = cur_tick_ms() - pull_start_time

        out_meta['profile'].update({
            'consumer': {
                'pull_time': pull_time,
            },
        })
        current_app.logger.debug(f'DMERGE profile: {out_meta["profile"]}')
        return out_meta

    consumer_dispatcher = {
        'S3': consumer_s3,
        'DMERGE': consumer_dmerge,
        'RPC': consumer_rpc
    }
    dispatch_key = event['features']['protocol']
    out_dict = consumer_dispatcher[dispatch_key](event)
    out_dict['profile']['wf_end_tick'] = cur_tick_ms()
    out_dict['profile']['leave_tick'] = cur_tick_ms()
    out_dict['profile'][stage_name]['stage_time'] = sum(out_dict['profile'][stage_name].values())

    return out_dict


def sink(metas):
    for i, meta in enumerate(metas):
        current_app.logger.debug(f"@{i}:[ {util.PROTOCOL} ] "
                                 f"whole profile: {meta['profile']}")
    meta = metas[-1]
    current_app.logger.info(f"[ {util.PROTOCOL} ] "
                            f"whole profile: {meta['profile']}")
    meta['profile']['runtime']['stage_time'] = sum(meta['profile']['runtime'].values())

    reduced_profile = util.reduce_profile(meta['profile'])
    e2e_time = meta['profile']['wf_end_tick'] - meta['profile']['wf_start_tick']
    current_app.logger.info(f"[ {util.PROTOCOL} ] "
                            f"workflow e2e time for whole: {e2e_time}")
    current_app.logger.info(f"[ {util.PROTOCOL} ] "
                            f"workflow e2e time: {reduced_profile['stage_time']}")
    for k, v in reduced_profile.items():
        current_app.logger.info(f"Part@ {k} passed {v} ms")
    return {}


def default_handler(meta):
    current_app.logger.error(f'not a default path for type')
    return meta


if __name__ == '__main__':
    res = producer({})
