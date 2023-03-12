import json
import os
import uuid
from multiprocessing import Process, Manager

import lightgbm as lgb
import numpy as np
from flask import current_app
from minio import Minio
from numpy.linalg import eig
import util
from util import cur_tick_ms, fill_gid

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


def source(meta):
    data_path = 'dataset/Digits_Train.txt'
    out_meta = {
        'statusCode': 200,
        'wf_id': str(uuid.uuid4()),
        'trainer_num': int(os.environ.get('TRAINER_NUM', 4)),
    }

    def source_s3(meta):
        s3_object_key = 'digits'
        tick = cur_tick_ms()
        s3_client.fput_object(bucket_name, s3_object_key, data_path)
        sd_time = cur_tick_ms() - tick
        meta['s3_obj_key'] = s3_object_key
        meta['profile'] = {
            'source': {
                'sd_time': sd_time,
            },
            'leave_tick': cur_tick_ms(),
        }
        return meta

    def source_dmerge(meta):
        tick = cur_tick_ms()
        train_data = np.genfromtxt(data_path, delimiter='\t')
        execute_time = cur_tick_ms() - tick
        addr = int(os.environ.get('BASE_HEX', '100000000'), 16)
        out_meta = dict(meta)

        push_start_time = cur_tick_ms()
        train_data_li = train_data.tolist()
        global_obj['train_data'] = train_data_li

        nic_idx = 0
        gid, mac_id, hint = util.push(nic_id=nic_idx, peak_addr=addr)
        push_time = cur_tick_ms() - push_start_time

        obj_id = id(global_obj["train_data"])
        current_app.logger.debug(f'gid is {gid} ,'
                                 f'ObjectID is {obj_id} ,'
                                 f'hint is {hint} ,'
                                 f'mac id {mac_id} ,'
                                 f'base addr in {hex(addr)}')
        out_meta['profile'] = {
            'source': {
                'execute_time': execute_time,
                'push_time': push_time,
            },
            'leave_tick': cur_tick_ms()
        }
        out_meta['obj_hash'] = {
            'train_data': obj_id
        }
        out_meta['route'] = {
            'gid': gid,
            'machine_id': mac_id,
            'nic_id': nic_idx,
            'hint': hint
        }
        return out_meta

    source_dispatch = {
        'S3': source_s3,
        'DMERGE': source_dmerge,
        'P2P': source_s3
    }
    out_dict = source_dispatch[util.PROTOCOL](out_meta)
    out_dict['profile']['source']['stage_time'] = sum(out_dict['profile']['source'].values())
    return out_dict


def pca(meta):
    local_data_path = '/tmp/digits.txt'
    start_time = cur_tick_ms()

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
        execute_time = 0
        sd_time = 0
        s3_time = 0

        out_meta = dict(_meta)
        s3_obj = meta['s3_obj_key']
        tick = cur_tick_ms()
        s3_client.fget_object(bucket_name, s3_obj, local_data_path)  # download all
        s3_time += cur_tick_ms() - tick

        tick = cur_tick_ms()
        train_data = np.genfromtxt(local_data_path, delimiter='\t')
        sd_time += cur_tick_ms() - tick

        # Execute
        tick = cur_tick_ms()
        vectors, first_n_A_label = execute_body(train_data)
        execute_time += cur_tick_ms() - tick
        # Deserialize
        tick = cur_tick_ms()
        np.save("/tmp/vectors_pca.txt", vectors)
        np.savetxt("/tmp/Digits_Train_Transform.txt", first_n_A_label, delimiter="\t")
        sd_time += cur_tick_ms() - tick

        # dump to s3
        tick = cur_tick_ms()
        s3_client.fput_object(bucket_name, 'ML_Pipeline/vectors_pca.txt', '/tmp/vectors_pca.txt.npy')
        s3_client.fput_object(bucket_name, 'ML_Pipeline/train_pca_transform_2.txt',
                              '/tmp/Digits_Train_Transform.txt')
        s3_time += cur_tick_ms() - tick

        out_meta['s3_obj_key'] = 'ML_Pipeline/train_pca_transform_2.txt'
        out_meta['profile']['pca'] = {
            'execute_time': execute_time,
            'sd_time': sd_time,
            's3_time': s3_time
        }
        return out_meta

    def pca_dmerge(_meta, data):
        out_meta = dict(_meta)
        target_id = _meta['obj_hash']['train_data']
        route = _meta['route']
        gid, mac_id, hint, nic_id = route['gid'], route['machine_id'], \
            route['hint'], route['nic_id']
        pull_start_time = cur_tick_ms()

        util.pull(mac_id, hint)
        obj = util.fetch(target_id)
        data = np.array(obj)

        pull_time = cur_tick_ms() - pull_start_time

        execute_start_time = cur_tick_ms()
        vectors, first_n_A_label = execute_body(data)
        execute_time = cur_tick_ms() - execute_start_time

        push_start_time = cur_tick_ms()
        addr = int(os.environ.get('BASE_HEX', '100000000'), 16)
        first_n_A_label_li = first_n_A_label.tolist()
        # global_obj['vectors'] = vectors_li
        global_obj['first_n_A_label'] = first_n_A_label_li

        nic_idx = 0
        gid, mac_id, hint = util.push(nic_id=nic_idx, peak_addr=addr)
        push_time = cur_tick_ms() - push_start_time

        first_n_A_label_obj_id = id(global_obj["first_n_A_label"])
        current_app.logger.info(f'gid is {gid} ,'
                                f'first_n_A_label_obj_id is {first_n_A_label_obj_id} ,'
                                f'hint is {hint} ,'
                                f'mac id {mac_id} ,'
                                f'base addr in {hex(addr)}')

        nt_time = start_time - _meta['profile']['leave_tick']
        out_meta['obj_hash'] = {
            'first_n_A_label': first_n_A_label_obj_id,
        }
        out_meta['route'] = {
            'gid': gid,
            'machine_id': mac_id,
            'nic_id': nic_idx,
            'hint': hint
        }
        # out_meta['s3_obj_key'] = 'ML_Pipeline/train_pca_transform_2.txt'
        out_meta['profile'].update({
            'pca': {
                'execute_time': execute_time,
                'pull_time': pull_time,
                'push_time': push_time,
                'nt_time': nt_time
            },
            'leave_tick': cur_tick_ms()
        })
        current_app.logger.debug(f'DMERGE profile: {out_meta}')
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

        current_app.logger.debug(f"PCA post_handle meta: {returnedDic}")
        return returnedDic

    pca_dispatcher = {
        'S3': pca_s3,
        'DMERGE': pca_dmerge
    }
    dispatch_key = util.PROTOCOL
    returnedDic = pca_dispatcher[dispatch_key](meta, None)
    out_dict = post_handle(returnedDic)
    end_time = cur_tick_ms()
    out_dict['profile'].update({
        'wf_start_tick': start_time,
        'leave_tick': end_time,
    })
    out_dict['profile']['pca']['stage_time'] = sum(out_dict['profile']['pca'].values())
    return out_dict


def trainer(meta):
    start_time = cur_tick_ms()
    nt_time = start_time - meta['profile']['leave_tick']

    def train_tree(t_index, X_train, y_train, event, num_of_trees, max_depth, feature_fraction, return_dict, runs,
                   process_dict, upload_dict):
        start_process = cur_tick_ms()
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

        start_upload = cur_tick_ms()
        model_name = "lightGBM_model_" + str(_id) + ".txt"
        save_path = "tmp/" + model_name
        gbm.save_model(save_path)
        s3_client.fput_object(bucket_name, "ML_Pipeline/" + model_name, save_path)
        end_upload = cur_tick_ms()

        return_dict[str(runs) + "_" + str(max_depth) + "_" + str(feature_fraction)] = acc
        process_dict[str(runs) + "_" + str(max_depth) + "_" + str(feature_fraction)] = (end_process - start_process)
        upload_dict[str(runs) + "_" + str(max_depth) + "_" + str(feature_fraction)] = (end_upload - start_upload)

        return {
            'statusCode': 200,
            'body': json.dumps('Done Training With Accuracy = ' + str(acc)),
            '_id': _id,
            'key1': event['key1']
        }

    def execute_body(event, train_data):
        y_train = train_data[:5000, 0]
        X_train = train_data[:5000, 1:train_data.shape[1]]
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
        upload_time = sum(upload_dict.values())
        exe_time = sum(process_dict.values())
        current_app.logger.debug(f"process dict: {process_dict}")
        return return_dict, exe_time, upload_time

    def trainer_s3(meta, data):
        out_meta = dict(meta)
        id = int(os.environ.get("ID"))
        event = meta['detail']['indeces'][int(id)]

        s3_time = 0
        sd_time = 0
        exe_time = 0

        tick = cur_tick_ms()
        filename = "/tmp/Digits_Train_Transform.txt"
        s3_obj_key = meta['s3_obj_key']
        s3_client.fget_object(bucket_name, s3_obj_key, filename)
        s3_time += cur_tick_ms() - tick

        tick = cur_tick_ms()
        train_data = np.genfromtxt(filename, delimiter='\t')
        sd_time += cur_tick_ms() - tick

        return_dict, execute_body_time, upload_time = execute_body(event, train_data)
        exe_time += execute_body_time
        s3_time += upload_time

        out_meta.update({
            'statusCode': 200,
            'trees_max_depthes': return_dict.keys(),
            'accuracies': return_dict.values(),
        })
        out_meta['profile']['train'] = {
            'execute_time': exe_time,
            's3_time': s3_time,
            'sd_time': sd_time,
            'nt_time': nt_time
        }
        out_meta.pop('detail')
        current_app.logger.debug(f"Inner Trainer s3 with meta: {out_meta}")
        return out_meta

    def trainer_dmerge(meta, _data):
        out_meta = dict(meta)
        event = meta['detail']['indeces'][int(os.environ.get("ID"))]
        route = meta['route']
        gid, mac_id, hint, nic_id = route['gid'], route['machine_id'], \
            route['hint'], route['nic_id']
        current_app.logger.info(f"trainer dmerge meta is {meta}")
        # # Pull
        pull_start_time = cur_tick_ms()
        util.pull(mac_id, hint)
        train_data = util.fetch(meta['obj_hash']['first_n_A_label'])

        current_app.logger.info(f"data len is {len(train_data)}. ")
        pull_time = cur_tick_ms() - pull_start_time
        # Execute
        # return_dict, execute_body_time, upload_time = execute_body(event, train_data)
        # exe_time = execute_body_time
        # s3_time = upload_time

        out_meta.update({
            'statusCode': 200,
            # 'trees_max_depthes': return_dict.keys(),
            # 'accuracies': return_dict.values(),
        })
        out_meta['profile']['train'] = {
            # 'execute_time': exe_time,
            # 's3_time': s3_time,
            'pull_time': pull_time,
            'nt_time': nt_time,
        }
        out_meta.pop('detail')
        current_app.logger.info(f"Inner Trainer s3 with meta: {out_meta}")
        return out_meta

    trainer_dispatcher = {
        'S3': trainer_s3,
        'DMERGE': trainer_dmerge
    }

    out_dict = trainer_dispatcher[util.PROTOCOL](meta, None)
    end_time = cur_tick_ms()
    out_dict['profile']['leave_tick'] = end_time
    out_dict['profile']['train']['stage_time'] = sum(out_dict['profile']['train'].values())
    return out_dict


def combinemodels(metas):
    start_time = cur_tick_ms()

    def combine_models_s3(_metas, data):
        out_meta = _metas[-1]
        prev_leave_tick = out_meta['profile']['leave_tick']

        for event in _metas:
            # TODO: Finish reduce
            pass

        out_meta['profile'].update({
            'combinemodels': {
                'nt_time': start_time - prev_leave_tick
            },
        })
        for i, meta in enumerate(_metas):
            current_app.logger.info(f"@{i} Inner combine_models s3 with meta: {meta}")
        # TODO: aggregate the result
        return out_meta

    event = metas[-1]
    combine_models_dispatcher = {
        'S3': combine_models_s3,
        'DMERGE': combine_models_s3
    }
    out_dict = combine_models_dispatcher[util.PROTOCOL](metas, None)
    out_dict['profile']['combinemodels']['stage_time'] = \
        sum(out_dict['profile']['combinemodels'].values())
    return out_dict


def sink(meta):
    def calculate_time(profile):
        total_time = 0
        remove_keys = set()
        for stage in profile:
            value = profile[stage]
            if type(value) == dict:
                total_time += value.get('stage_time', 0)
            else:
                remove_keys.add(stage)
        for st in remove_keys:
            profile.pop(st)
        return total_time

    total_time = calculate_time(meta['profile'])
    meta['profile'].update({
        'wf_e2e_time': total_time,
    })
    current_app.logger.info(f"Profile result: {meta['profile']}")
    return {
        'data': meta
    }


def default_handler(meta):
    current_app.logger.warn(f'not a default path for type')
    return meta
