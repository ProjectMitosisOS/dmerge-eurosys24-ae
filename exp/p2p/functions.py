import copy

from minio import Minio
import uuid
import os
from flask import current_app
from util import cur_tick_ms

from bindings import *

s3_client = Minio(
    endpoint='minio:9000',
    secure=False,
    access_key='ACCESS_KEY', secret_key='SECRET_KEY')
bucket_name = 'p2p'
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


stageTimeStr = 'stage_time'
executeTimeStr = 'execute_time'
interactTimeStr = 'interact_time'
serializeTimeStr = 'serialize_time'
deserializeTimeStr = 'deserialize_time'
networkTimeStr = 'network_time'


def splitter(meta):
    data_path = 'data/digits.txt'
    s3_client.fput_object(bucket_name, 'digits', data_path)
    current_app.logger.info(f'splitter, {meta}')
    return {
        'status': 200,
        's3_obj_key': 'digits',
        'wf_id': str(uuid.uuid4()),
        'features': {
            'protocol': os.environ.get('PROTOCOL', 'S3')  # value of DMERGE / S3 / P2P --- Default as S3
        },
        'profile': {
            'leave_tick': cur_tick_ms()
        },

    }


import numpy as np
from numpy.linalg import eig

global_obj = {}


def producer(meta):
    def execute_body(data):
        return data

    def producer_s3(_meta, data):
        filename = "/tmp/data.txt"
        execute_start_time = cur_tick_ms()
        out_data = execute_body(data)
        execute_end_time = cur_tick_ms()

        sd_start_time = cur_tick_ms()
        np.savetxt(filename, out_data, delimiter='\t')
        out_meta = dict(_meta)
        s3_obj_key = 'Data.txt'
        s3_client.fput_object(bucket_name, s3_obj_key, filename)
        sd_end_time = cur_tick_ms()

        out_meta['s3_obj_key'] = s3_obj_key

        out_meta['profile'].update({
            'producer': {
                'execute_time': execute_end_time - execute_start_time,
                'sd_time': sd_end_time - sd_start_time,
            },
            'leave_tick': cur_tick_ms()
        })
        current_app.logger.info(f'S3 profile: {out_meta["profile"]}')

        return out_meta

    def producer_dmerge(_meta, data):
        out_data = execute_body(data)

        global_obj['data'] = out_data

        addr = int(os.environ.get('BASE_HEX', '100000000'), 16)
        out_meta = dict(_meta)

        sd = sopen()
        gid, mac_id = syscall_get_gid(sd=sd, nic_idx=0)
        gid = fill_gid(gid)
        hint = call_register(sd=sd, peak_addr=addr)

        obj_id = id(global_obj["data"])
        current_app.logger.info(f'gid is {gid} ,'
                                f'ObjectID is {id(global_obj["data"])} ,'
                                f'hint is {hint} ,'
                                f'mac id {mac_id} ,'
                                f'addr in {hex(addr)}')

        out_meta.pop('s3_obj_key')
        out_meta['obj_hash'] = {
            'data': obj_id
        }
        out_meta['route'] = {
            'gid': gid,
            'machine_id': mac_id,
            'nic_id': 1,
            'hint': hint
        }

    s3_obj = meta['s3_obj_key']
    local_data_path = '/tmp/digits.txt'
    s3_client.fget_object(bucket_name, s3_obj, local_data_path)  # download all
    data = np.genfromtxt(local_data_path, delimiter='\t')
    producer_dispatcher = {
        'S3': producer_s3,
        'DMERGE': producer_dmerge,
        'P2P': producer_s3
    }
    dispatch_key = meta['features']['protocol']
    return producer_dispatcher[dispatch_key](meta, data)


def consumer(metas):
    def execute_body(data):
        train_labels = data[:, 0]
        A = data[:, 1:data.shape[1]]
        MA = np.mean(A.T, axis=1)
        CA = A - MA
        VA = np.cov(CA.T)
        values, vectors = eig(VA)
        PA = vectors.T.dot(CA.T)

        return vectors

    def consumer_s3(_metas):
        out_meta = _metas[-1]
        sd_time = 0
        execute_time = 0
        nt_time = 0
        start_tick = cur_tick_ms()
        for event in _metas:
            s3_obj_key = event['s3_obj_key']

            sd_start_time = cur_tick_ms()
            local_data_path = '/tmp/digits.txt'
            s3_client.fget_object(bucket_name, s3_obj_key, local_data_path)
            data = np.genfromtxt(local_data_path, delimiter='\t')
            sd_end_time = cur_tick_ms()

            execute_start_time = cur_tick_ms()
            execute_body(data)
            execute_end_time = cur_tick_ms()

            sd_time += sd_end_time - sd_start_time
            execute_time += execute_end_time - execute_start_time
            nt_time += start_tick - event['profile']['leave_tick']

        out_meta['profile'].update({
            'consumer': {
                'execute_time': execute_time,
                'sd_time': sd_time,
                'network_time': nt_time
            },
            'leave_tick': cur_tick_ms()
        })
        current_app.logger.info(f'S3 profile: {out_meta["profile"]}')
        return out_meta

    def consumer_dmerge(_metas):
        for event in _metas:
            target_id = event['obj_hash']['data']
            current_app.logger.info(f'consumer with meta: {metas}. Target id {hex(target_id)}')

            route = event['route']
            gid, mac_id, hint, nic_id = route['gid'], route['machine_id'], \
                route['hint'], route['nic_id']

            sd = sopen()

            res = syscall_connect_session(
                sd, gid, machine_id=mac_id, nic_id=nic_id)
            current_app.logger.info(f"connect res {res}. gid: {gid} ,"
                                    f"machine id {mac_id} ,"
                                    f"hint {hint} ,"
                                    f"nic id {nic_id}")

            res = call_pull(sd=sd, hint=hint, machine_id=mac_id)
            obj = id_deref(target_id, None)
            current_app.logger.info(f'get result as {obj}')
            return event

    event = metas[-1]
    consumer_dispatcher = {
        'S3': consumer_s3,
        'DMERGE': consumer_dmerge,
        'P2P': consumer_s3
    }
    dispatch_key = event['features']['protocol']
    return consumer_dispatcher[dispatch_key](metas)


def sink(metas):
    current_app.logger.info(f'sink, {metas}.')
    return {
        'data': metas
    }


def default_handler(meta):
    current_app.logger.info(f'not a default path for type')
    return meta


if __name__ == '__main__':
    res = producer({})
