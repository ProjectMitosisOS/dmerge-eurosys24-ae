import copy

from minio import Minio
import uuid
import os
from flask import current_app
from util import cur_tick_ms
import numpy as np
from numpy.linalg import eig

global_obj = {}

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


def source(meta):
    return {
        'status': 200,
        # 's3_obj_key': 'digits',
        'wf_id': str(uuid.uuid4()),
        'features': {
            'protocol': os.environ.get('PROTOCOL', 'S3')  # value of DMERGE / S3 / P2P --- Default as S3
        },
        'profile': {
            'leave_tick': cur_tick_ms()
        },
    }


def pca(meta):
    def pca_s3(_meta, data):
        out_meta = dict(_meta)
        current_app.logger.info(f"Inner pca s3 with meta: {out_meta}")
        return out_meta

    pca_dispatcher = {
        'S3': pca_s3
    }
    dispatch_key = meta['features']['protocol']
    return pca_dispatcher[dispatch_key](meta, None)


def trainer(metas):
    def trainer_s3(_metas, data):
        out_meta = _metas[-1]
        current_app.logger.info(f"Inner Trainer s3 with meta: {out_meta}")
        return out_meta

    event = metas[-1]
    trainer_dispatcher = {
        'S3': trainer_s3
    }
    dispatch_key = event['features']['protocol']
    return trainer_dispatcher[dispatch_key](metas, None)


def combinemodels(metas):
    def combine_models_s3(_metas, data):
        out_meta = _metas[-1]
        current_app.logger.info(f"Inner combine_models s3 with meta: {out_meta}")
        return out_meta

    event = metas[-1]
    combine_models_dispatcher = {
        'S3': combine_models_s3
    }
    dispatch_key = event['features']['protocol']
    return combine_models_dispatcher[dispatch_key](metas, None)


def sink(metas):
    current_app.logger.info(f'sink, {metas}.')
    return {
        'data': metas
    }


def default_handler(meta):
    current_app.logger.info(f'not a default path for type')
    return meta
