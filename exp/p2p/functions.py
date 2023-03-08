import copy

from minio import Minio
import uuid
import os
from flask import current_app

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
    data = np.genfromtxt(local_data_path, delimiter='\t')
    global_obj['data'] = data
    out_meta = dict(meta)

    out_meta.pop('s3_obj_key')
    out_meta['obj_hash'] = {
        'data': id(global_obj['data'])
    }
    return out_meta


def consumer(metas):
    target_id = metas[-1]['obj_hash']['data']
    current_app.logger.info(f'consumer with meta: {metas}. Target id {hex(target_id)}')

    return metas[-1] if len(metas) > 0 else 0


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
