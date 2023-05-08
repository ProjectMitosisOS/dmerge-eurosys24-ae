import json
import os
import pickle
import uuid
from multiprocessing import Process, Manager

import lightgbm as lgb
import numpy as np
from flask import current_app
from minio import Minio
from numpy.linalg import eig

import util
from util import cur_tick_ms

global_obj = {}

from bindings import *

s3_client = Minio(
    endpoint='minio:9000',
    secure=False,
    access_key='ACCESS_KEY', secret_key='SECRET_KEY')
bucket_name = 'ml-pipeline'
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


def source(_meta):
    out_meta = {
        'statusCode': 200,
        'wf_id': str(uuid.uuid4()),
        'trainer_num': int(os.environ.get('TRAINER_NUM', 4)),
        'profile': {
            'sd_bytes_len': 0,
            'runtime': {
                'sd_time': 0,
                'fetch_data_time': 0,
                'nt_time': 0,
            }
        },
    }
    return out_meta


def pca(meta):
    local_data_path = 'dataset/Digits_Train.txt'

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

    def pca_es(_meta, train_data):
        out_meta = dict(_meta)

        # Execute
        tick = cur_tick_ms()
        vectors, first_n_A_label = execute_body(train_data)
        execute_time = cur_tick_ms() - tick
        # Deserialize
        tick = cur_tick_ms()
        vectors_o = pickle.dumps(vectors.tolist())
        first_n_A_label_o = pickle.dumps(first_n_A_label.tolist())
        out_meta['profile']['sd_bytes_len'] += len(vectors_o) + len(first_n_A_label_o)
        sd_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        obj_key = 'ML_Pipeline/train_pca_transform_2.txt'
        util.redis_put('ML_Pipeline/vectors_pca.txt', vectors_o)
        util.redis_put(obj_key, first_n_A_label_o)
        es_time = cur_tick_ms() - tick

        out_meta['s3_obj_key'] = obj_key
        out_meta['profile']['pca'] = {
            'execute_time': execute_time,
            'sd_time': sd_time,
            'es_time': es_time,
        }
        return out_meta

    def pca_rrpc(_meta, train_data):
        return _meta

    def pca_rpc(_meta, train_data):
        out_meta = dict(_meta)

        # Execute
        tick = cur_tick_ms()
        vectors, first_n_A_label = execute_body(train_data)
        execute_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        out_meta['payload'] = {
            'vectors': vectors.tolist(),
            'first_n_A_label': first_n_A_label.tolist()
        }
        sd_time = cur_tick_ms() - tick

        out_meta['profile']['pca'] = {
            'execute_time': execute_time,
            'sd_time': sd_time,
        }
        return out_meta

    def pca_dmerge(_meta, train_data):
        out_meta = dict(_meta)

        execute_start_time = cur_tick_ms()
        vectors, first_n_A_label = execute_body(train_data)
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
        current_app.logger.debug(f'gid is {gid} ,'
                                 f'first_n_A_label_obj_id is {first_n_A_label_obj_id} ,'
                                 f'hint is {hint} ,'
                                 f'mac id {mac_id} ,'
                                 f'base addr in {hex(addr)}')

        out_meta['obj_hash'] = {
            'first_n_A_label': first_n_A_label_obj_id,
        }
        out_meta['route'] = {
            'gid': gid,
            'machine_id': mac_id,
            'nic_id': nic_idx,
            'hint': hint
        }
        out_meta['profile'].update({
            'pca': {
                'execute_time': execute_time,
                'push_time': push_time,
            },
            'leave_tick': cur_tick_ms()
        })
        current_app.logger.debug(f'DMERGE profile: {out_meta}')
        return out_meta

    def post_handle(returnedDic):
        mapper_num = int(returnedDic['trainer_num'])
        list_hyper_params = []
        epochs = int(os.environ.get('EPOCH', '10'))

        for feature_fraction in [0.5, 0.5, 0.5, 0.5]:
            max_depth = 10
            for num_of_trees in [epochs, epochs, epochs, epochs]:
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
                     "feature_fraction": feature_fraction, "threads": 6,
                     "leave_tick": cur_tick_ms()}
                num_of_trees = []
                max_depth = []
                feature_fraction = []
                returnedDic["detail"]["indeces"].append(j)

        current_app.logger.debug(f"PCA post_handle meta: {returnedDic}")
        return returnedDic

    train_data = np.genfromtxt(local_data_path, delimiter='\t')
    data_ratio = int(os.environ.get('DATA_RAIO', '100'))
    sz = int(len(train_data) * data_ratio / 100)
    data = train_data[:sz, :]
    meta['profile']['wf_start_tick'] = cur_tick_ms()

    pca_dispatcher = {
        'ES': pca_es,
        'RRPC': pca_rrpc,
        'RPC': pca_rpc,
        'DMERGE': pca_dmerge,
        'DMERGE_PUSH': pca_dmerge,
    }
    dispatch_key = util.PROTOCOL
    returnedDic = pca_dispatcher[dispatch_key](meta, data)
    out_dict = post_handle(returnedDic)
    out_dict['profile']['pca']['stage_time'] = sum(out_dict['profile']['pca'].values())
    return out_dict


def trainer(meta):
    def train_tree(t_index, X_train, y_train, event, num_of_trees, max_depth,
                   feature_fraction, return_dict, runs,
                   process_dict, upload_dict, sd_dict):
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

        tick = cur_tick_ms()
        o = pickle.dumps(gbm)
        sd_time = cur_tick_ms() - tick

        start_upload = cur_tick_ms()
        model_name = "lightGBM_model_" + str(_id) + ".txt"
        util.redis_put(model_name, o)
        end_upload = cur_tick_ms()

        return_dict[str(runs) + "_" + str(max_depth) + "_" + str(feature_fraction)] = acc
        process_dict[str(runs) + "_" + str(max_depth) + "_" + str(feature_fraction)] = (end_process - start_process)
        upload_dict[str(runs) + "_" + str(max_depth) + "_" + str(feature_fraction)] = (end_upload - start_upload)
        sd_dict[str(runs) + "_" + str(max_depth) + "_" + str(feature_fraction)] = sd_time

        return {
            'statusCode': 200,
            'body': json.dumps('Done Training With Accuracy = ' + str(acc)),
            '_id': _id,
            'key1': event['key1']
        }

    def execute_body(event, train_data):
        sz = len(train_data)
        y_train = train_data[:sz, 0]
        X_train = train_data[:sz, 1:train_data.shape[1]]
        manager = Manager()
        return_dict = manager.dict()
        process_dict = manager.dict()
        upload_dict = manager.dict()
        sd_dict = manager.dict()
        num_of_trees = event['num_of_trees']
        depthes = event['max_depth']
        feature_fractions = event['feature_fraction']
        current_app.logger.debug(f"Ready to start {num_of_trees} processes. Meta is {event}")

        for runs in range(len(num_of_trees)):
            # Use multiple processes to train trees in parallel
            threads = event['threads']
            ths = []
            for t in range(threads):
                ths.append(Process(target=train_tree, args=(
                    t, X_train, y_train, event, num_of_trees[runs], depthes[runs], feature_fractions[runs],
                    return_dict, num_of_trees[runs], process_dict, upload_dict, sd_dict)))
            for t in range(threads):
                ths[t].start()
            for t in range(threads):
                ths[t].join()
        upload_time = sum(upload_dict.values())
        exe_time = sum(process_dict.values())
        sd_time = sum(sd_dict.values())
        return return_dict, exe_time, upload_time, sd_time

    def trainer_es(meta):
        out_meta = dict(meta)
        id = int(os.environ.get("ID"))
        event = meta['detail']['indeces'][int(id)]

        tick = cur_tick_ms()
        s3_obj_key = meta['s3_obj_key']
        obj_o = util.redis_get(s3_obj_key)
        es_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        train_data = np.array(pickle.loads(obj_o))
        sd_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        return_dict, execute_body_time, upload_time, sd_times = execute_body(event, train_data)
        process_passed = cur_tick_ms() - tick - execute_body_time - upload_time - sd_times
        out_meta['profile']['wf_start_tick'] += process_passed
        exe_time = execute_body_time
        es_time += upload_time
        sd_time += sd_times

        out_meta.update({
            'statusCode': 200,
            'trees_max_depthes': return_dict.keys(),
            'accuracies': return_dict.values(),
        })
        out_meta['profile']['train'] = {
            'execute_time': exe_time,
            'es_time': es_time,
            'sd_time': sd_time,
        }
        out_meta.pop('detail')
        current_app.logger.debug(f"Inner Trainer s3 with meta: {out_meta}")
        return out_meta

    def trainer_rrpc(meta):
        return trainer_dmerge(meta)

    def trainer_rpc(meta):
        out_meta = dict(meta)
        id = int(os.environ.get("ID"))
        event = meta['detail']['indeces'][int(id)]

        tick = cur_tick_ms()
        train_data = np.array(meta['payload']['first_n_A_label'])
        sd_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        return_dict, execute_body_time, upload_time, sd_times = execute_body(event, train_data)
        process_passed = cur_tick_ms() - tick - execute_body_time - upload_time - sd_times
        out_meta['profile']['wf_start_tick'] += process_passed
        exe_time = execute_body_time
        es_time = upload_time
        sd_time += sd_times

        out_meta.update({
            'statusCode': 200,
            'trees_max_depthes': return_dict.keys(),
            'accuracies': return_dict.values(),
        })
        out_meta['profile']['train'] = {
            'execute_time': exe_time,
            'sd_time': sd_time,
            'es_time': es_time,
        }
        out_meta.pop('detail')
        out_meta.pop('payload')
        current_app.logger.debug(f"Inner Trainer s3 with meta: {out_meta}")
        return out_meta

    def trainer_dmerge(meta):
        out_meta = dict(meta)
        event = meta['detail']['indeces'][int(os.environ.get("ID"))]
        route = meta['route']
        gid, mac_id, hint, nic_id = route['gid'], route['machine_id'], \
            route['hint'], route['nic_id']
        current_app.logger.debug(f"trainer dmerge meta is {meta}")
        # # Pull
        pull_start_time = cur_tick_ms()
        util.pull(mac_id, hint)
        data = util.fetch(meta['obj_hash']['first_n_A_label'])
        pull_time = cur_tick_ms() - pull_start_time
        # Execute
        train_data = np.array(data)
        tick = cur_tick_ms()
        return_dict, execute_body_time, upload_time, sd_times = execute_body(event, train_data)
        process_passed = cur_tick_ms() - tick - execute_body_time - upload_time - sd_times
        out_meta['profile']['wf_start_tick'] += process_passed
        exe_time = execute_body_time

        out_meta.update({
            'statusCode': 200,
            'trees_max_depthes': return_dict.keys(),
            'accuracies': return_dict.values(),
        })
        out_meta['profile']['train'] = {
            'execute_time': exe_time,
            'pull_time': pull_time,
        }
        out_meta.pop('detail')
        current_app.logger.info(f"Inner Trainer s3 with meta: {out_meta}")
        return out_meta

    trainer_dispatcher = {
        'ES': trainer_es,
        'RRPC': trainer_rrpc,
        'RPC': trainer_rpc,
        'DMERGE': trainer_dmerge,
        'DMERGE_PUSH': trainer_dmerge
    }

    out_dict = trainer_dispatcher[util.PROTOCOL](meta)
    out_dict['profile']['train']['stage_time'] = sum(out_dict['profile']['train'].values())
    return out_dict


def combinemodels(metas):
    def combine_models(_metas):
        out_meta = dict(_metas[-1])
        le = len(_metas)

        P = {}
        for event in _metas:
            profile = event['profile']
            for k, v in profile.items():
                if isinstance(v, dict):
                    if k not in P.keys():
                        P[k] = {}
                    for stage, _time in v.items():
                        if stage not in P[k].keys():
                            P[k][stage] = 0
                        P[k][stage] += _time / le
                else:
                    P[k] = v
        out_meta['profile'] = P
        out_meta['profile'].update({
            'combinemodels': {},
        })
        for i, meta in enumerate(_metas):
            current_app.logger.debug(f"@{i} Inner combine_models s3 with Profile: {meta['profile']}")
        return out_meta

    out_dict = combine_models(metas)
    out_dict['profile']['wf_e2e_time'] = \
        cur_tick_ms() - out_dict['profile']['wf_start_tick']
    out_dict['profile']['combinemodels']['stage_time'] = \
        sum(out_dict['profile']['combinemodels'].values())
    return out_dict


def sink(meta):
    profile = meta['profile']
    es_obj_sz = profile['sd_bytes_len']
    e2e = meta['profile']['wf_e2e_time']

    remove_set = set()
    for k in profile.keys():
        if not isinstance(profile[k], dict):
            remove_set.add(k)
    for k in remove_set:
        profile.pop(k)
    p = meta['profile']
    p['runtime']['stage_time'] = \
        sum(p['runtime'].values())
    reduced_profile = util.reduce_profile(p)
    current_app.logger.info(f"sd bytes len: {es_obj_sz} ")
    current_app.logger.info(f"Profile result: {p} ")
    current_app.logger.info(f"[ {util.PROTOCOL} ]E2E time: "
                            f"{reduced_profile['stage_time']}")
    for k, v in reduced_profile.items():
        current_app.logger.info(f"Part@ {k} passed {v} ms")
    return {
        'data': meta
    }


def default_handler(meta):
    current_app.logger.warn(f'not a default path for type')
    return meta
