import copy
import json
from multiprocessing import Process, Manager

from minio import Minio
import uuid
import os
from flask import current_app
from util import cur_tick_ms
import numpy as np
from numpy.linalg import eig
import lightgbm as lgb

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
        'statusCode': 200,
        's3_obj_key': s3_object_key,
        'wf_id': str(uuid.uuid4()),
        'trainer_num': 2,
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

    def post_handle(returnedDic):
        mapper_num = int(returnedDic['trainer_num'])
        list_hyper_params = []

        for feature_fraction in [0.25, 0.5, 0.75, 0.95]:
            max_depth = 10
            for num_of_trees in [5, 10, 15, 20]:
                list_hyper_params.append((num_of_trees, max_depth, feature_fraction))

        returnedDic["detail"] = {
            "indeces": []
        }

        num_of_trees = []
        max_depth = []
        feature_fraction = []
        num_bundles = 0
        count = 0
        bundle_size = len(list_hyper_params) / mapper_num
        for tri in list_hyper_params:  # of len 16
            feature_fraction.append(tri[2])
            max_depth.append(tri[1])
            num_of_trees.append(tri[0])
            count += 1
            if count >= bundle_size:
                count = 0
                num_bundles += 1
                j = {"mod_index": num_bundles,
                     "key1": "inv_300", "num_of_trees": num_of_trees, "max_depth": max_depth,
                     "feature_fraction": feature_fraction, "threads": 6, "start_tick": start_time,
                     "leave_tick": cur_tick_ms()}
                num_of_trees = []
                max_depth = []
                feature_fraction = []
                returnedDic["detail"]["indeces"].append(j)

        current_app.logger.info(f"PCA post_handle meta: {returnedDic}")
        return returnedDic

    start_time = cur_tick_ms()
    s3_obj = meta['s3_obj_key']
    s3_client.fget_object(bucket_name, s3_obj, local_data_path)  # download all
    train_data = np.genfromtxt(local_data_path, delimiter='\t')
    pca_dispatcher = {
        'S3': pca_s3
    }
    dispatch_key = meta['features']['protocol']
    returnedDic = pca_dispatcher[dispatch_key](meta, train_data)
    return post_handle(returnedDic)


def trainer(meta):
    def train_tree(t_index, X_train, y_train, event, num_of_trees, max_depth, feature_fraction, return_dict, runs,
                   process_dict, upload_dict):
        lgb_train = lgb.Dataset(X_train, y_train)
        _id = str(event['mod_index']) + "_" + str(t_index)
        chance = 0.8  # round(random.random()/2 + 0.5,1)
        params = {
            'boosting_type': 'gbdt',
            'objective': 'multiclass',
            'num_classes': 10,
            'metric': {'multi_logloss'},
            'num_leaves': 50,
            'learning_rate': 0.05,
            'feature_fraction': feature_fraction,
            'bagging_fraction': chance,  # If model indexes are 1->20, this makes feature_fraction: 0.7->0.9
            'bagging_freq': 5,
            'max_depth': max_depth,
            'verbose': -1,
            'num_threads': 2
        }
        print('Starting training...')
        start_process = cur_tick_ms()
        gbm = lgb.train(params,
                        lgb_train,
                        num_boost_round=num_of_trees,  # number of trees
                        valid_sets=lgb_train,
                        early_stopping_rounds=5)

        y_pred = gbm.predict(X_train, num_iteration=gbm.best_iteration)
        count_match = 0
        for i in range(len(y_pred)):
            result = np.where(y_pred[i] == np.amax(y_pred[i]))[0]
            if result == y_train[i]:
                count_match = count_match + 1
        acc = count_match / len(y_pred)
        end_process = cur_tick_ms()

        model_name = "lightGBM_model_" + str(_id) + ".txt"
        save_path = "tmp/" + model_name

        print("Ready to uploaded " + model_name)
        start_upload = cur_tick_ms()
        gbm.save_model(save_path)
        s3_client.fput_object(bucket_name, "ML_Pipeline/" + model_name, save_path)
        end_upload = cur_tick_ms()
        print("model uploaded " + model_name)

        return_dict[str(runs) + "_" + str(max_depth) + "_" + str(feature_fraction)] = acc
        process_dict[str(runs) + "_" + str(max_depth) + "_" + str(feature_fraction)] = (end_process - start_process)
        upload_dict[str(runs) + "_" + str(max_depth) + "_" + str(feature_fraction)] = (end_upload - start_upload)

        return {
            'statusCode': 200,
            'body': json.dumps('Done Training With Accuracy = ' + str(acc)),
            '_id': _id,
            'key1': event['key1']
        }

    def trainer_s3(meta, data):
        out_meta = dict(meta)
        id = int(os.environ.get("ID"))
        event = meta['detail']['indeces'][int(id)]

        filename = "/tmp/Digits_Train_Transform.txt"
        s3_obj_key = meta['s3_obj_key']
        s3_client.fget_object(bucket_name, s3_obj_key, filename)

        train_data = np.genfromtxt(filename, delimiter='\t')

        y_train = train_data[0:5000, 0]
        X_train = train_data[0:5000, 1:train_data.shape[1]]

        manager = Manager()
        return_dict = manager.dict()
        process_dict = manager.dict()
        upload_dict = manager.dict()
        num_of_trees = event['num_of_trees']
        depthes = event['max_depth']
        feature_fractions = event['feature_fraction']
        for runs in range(len(num_of_trees)):
            # Use multiple processes to train trees in parallel
            threads = event['threads']
            ths = []
            for t in range(threads):
                ths.append(Process(target=train_tree, args=(
                    t, X_train, y_train, event, num_of_trees[runs], depthes[runs], feature_fractions[runs],
                    return_dict, num_of_trees[runs], process_dict, upload_dict)))
            for t in range(threads):
                ths[t].start()
            for t in range(threads):
                ths[t].join()

        end_time = cur_tick_ms()
        out_meta.update({
            'statusCode': 200,
            'trees_max_depthes': return_dict.keys(),
            'accuracies': return_dict.values(),
            'leave_tick': end_time,
        })
        out_meta['profile'].update({
            'train': {
                'upload_model_time': upload_dict.values(),
                'train_process_time': process_dict.values()
            },
        })
        current_app.logger.info(f"Inner Trainer s3 with meta: {out_meta}")
        return out_meta

    trainer_dispatcher = {
        'S3': trainer_s3
    }

    dispatch_key = meta['features']['protocol']
    return trainer_dispatcher[dispatch_key](meta, None)


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
