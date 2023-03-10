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
    data_path = 'dataset/Digits_Train.txt'
    s3_object_key = 'digits'
    s3_client.fput_object(bucket_name, s3_object_key, data_path)
    wf_start_tick = cur_tick_ms()
    return {
        'status': 200,
        's3_obj_key': s3_object_key,
        'wf_id': str(uuid.uuid4()),
        'features': {
            'protocol': os.environ.get('PROTOCOL', 'S3')  # value of DMERGE / S3 / P2P --- Default as S3
        },
        'profile': {
            'leave_tick': wf_start_tick,
            'wf_start_tick': wf_start_tick
        },
    }


def pca(meta):
    local_data_path = '/tmp/digits.txt'

    def execute_body(train_data):
        train_labels = train_data[:, 0]
        A = train_data[:, 1:train_data.shape[1]]
        # calculate the mean of each column
        MA = np.mean(A.T, axis=1)
        # center columns by subtracting column means
        CA = A - MA
        # calculate covariance matrix of centered matrix
        VA = np.cov(CA.T)
        # eigendecomposition of covariance matrix
        values, vectors = eig(VA)
        # project data
        PA = vectors.T.dot(CA.T)
        train_labels = train_labels.reshape(train_labels.shape[0], 1)
        first_n_A = PA.T[:, 0:100].real
        first_n_A_label = np.concatenate((train_labels, first_n_A), axis=1)
        return vectors, first_n_A_label

    def pca_s3(_meta, data):
        out_meta = dict(_meta)
        # 1. Execute
        execute_start_time = cur_tick_ms()
        vectors, first_n_A_label = execute_body(data)
        execute_end_time = cur_tick_ms()
        # 2. Deserialize
        sd_start_time = cur_tick_ms()
        np.save("/tmp/vectors_pca.txt", vectors)
        np.savetxt("/tmp/Digits_Train_Transform.txt", first_n_A_label, delimiter="\t")
        sd_end_time = cur_tick_ms()
        s3_client.fput_object(bucket_name, 'ML_Pipeline/vectors_pca.txt', '/tmp/vectors_pca.txt.npy')
        # 3. dump to s3
        external_resource_start_time = cur_tick_ms()
        s3_client.fput_object(bucket_name, 'ML_Pipeline/train_pca_transform_2.txt',
                              '/tmp/Digits_Train_Transform.txt')
        external_resource_end_time = cur_tick_ms()

        out_meta['s3_obj_key'] = 'ML_Pipeline/train_pca_transform_2.txt'
        out_meta['profile'].update({
            'pca': {
                'execute_time': execute_end_time - execute_start_time,
                'sd_time': sd_end_time - sd_start_time,
                's3_time': external_resource_end_time - external_resource_start_time
            },
            'leave_tick': cur_tick_ms()
        })
        current_app.logger.info(f"Inner pca s3 with meta: {out_meta}")
        return out_meta

    s3_obj = meta['s3_obj_key']
    s3_client.fget_object(bucket_name, s3_obj, local_data_path)  # download all
    train_data = np.genfromtxt(local_data_path, delimiter='\t')
    pca_dispatcher = {
        'S3': pca_s3
    }
    dispatch_key = meta['features']['protocol']
    return pca_dispatcher[dispatch_key](meta, train_data)


def trainer(metas):
    def trainer_s3(_metas, data):
        out_meta = _metas[-1]
        for event in _metas:
            pass
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
        wf_end_tick = cur_tick_ms()
        for event in _metas:
            pass
        wf_start_tick = out_meta['profile']['wf_start_tick']
        out_meta['profile'].update({
            'wf_e2e_time': wf_end_tick - wf_start_tick
        })
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
