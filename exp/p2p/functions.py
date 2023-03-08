import copy

from minio import Minio
import uuid
import os
from flask import current_app
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
        'wf_id': str(uuid.uuid4())
    }


import numpy as np
from numpy.linalg import eig

global_obj = {}


def producer(meta):
    s3_obj = meta['s3_obj_key']
    local_data_path = '/tmp/digits.txt'
    worker_id = int(os.environ.get('ID', 0))

    current_app.logger.info(f'Get from s3 with key: {s3_obj}')
    s3_client.fget_object(bucket_name, s3_obj, local_data_path)  # download all
    # data = np.genfromtxt(local_data_path, delimiter='\t')
    addr = int(os.environ.get('BASE_HEX', '100000000'), 16)

    global_obj['data'] = [1, 3, 4]
    out_meta = dict(meta)

    sd = sopen()
    gid, mac_id = syscall_get_gid(sd=sd, nic_idx=0)
    gid = fill_gid(gid)
    hint = call_register(sd=sd, peak_addr=addr)
    # hint = 1
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
    return out_meta


def consumer(metas):
    event = metas[-1]
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


def sink(metas):
    current_app.logger.info(f'sink, {metas}. The len is {len(metas)}')
    return {
        'data': metas
    }


def default_handler(meta):
    current_app.logger.info(f'not a default path for type')
    return meta


if __name__ == '__main__':
    res = producer({})
