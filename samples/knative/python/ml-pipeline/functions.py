import json
import os
import time
from multiprocessing import Process, Manager

import lightgbm as lgb
import numpy as np
from minio import Minio
from numpy.linalg import eig

from util import cur_tick_ms

LOCAL_RUN = 0

s3_client = Minio(
    endpoint='minio:9000',
    secure=False,
    access_key='ACCESS_KEY', secret_key='SECRET_KEY')
bucket_name = 'ml-pipeline'
test_data_file_path = 'dataset/Digits_Test.txt'
train_data_file_path = 'dataset/Digits_Train.txt'

if not s3_client.bucket_exists(bucket_name):
    s3_client.make_bucket(bucket_name)
s3_client.fput_object(bucket_name, "ML_Pipeline/Digits_Train_org.txt", train_data_file_path)


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
    stage_name = "PCA"
    exe_time = 0
    interact_time = 0
    seri_time = 0
    desei_time = 0

    mapper_num = int(os.environ.get('MAPPER_NUM'))

    start_time = cur_tick_ms()
    # Step1: Download data from KV
    tick = cur_tick_ms()
    filename = "tmp/Digits_Train_Org.txt"
    s3_client.fget_object(bucket_name, "ML_Pipeline/Digits_Train_org.txt", filename)
    interact_time += cur_tick_ms() - tick
    # Deserialize the content into numpy array
    tick = cur_tick_ms()
    train_data = np.genfromtxt(filename, delimiter='\t')
    desei_time += cur_tick_ms() - tick

    # Step2: Execute Body of PCA
    tick = cur_tick_ms()
    ###########################
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
    first_n_A = PA.T[:, 0:100].real
    train_labels = train_labels.reshape(train_labels.shape[0], 1)
    first_n_A_label = np.concatenate((train_labels, first_n_A), axis=1)

    exe_time += cur_tick_ms() - tick

    tick = cur_tick_ms()
    np.save("tmp/vectors_pca.txt", vectors)
    np.savetxt("tmp/Digits_Train_Transform.txt", first_n_A_label, delimiter="\t")
    seri_time += cur_tick_ms() - tick

    tick = cur_tick_ms()
    # Upload to external
    s3_client.fput_object(bucket_name, 'ML_Pipeline/vectors_pca.txt', 'tmp/vectors_pca.txt.npy')
    s3_client.fput_object(bucket_name, 'ML_Pipeline/train_pca_transform_2.txt', 'tmp/Digits_Train_Transform.txt')
    interact_time += cur_tick_ms() - tick

    end_time = int(round(time.time() * 1000))

    list_hyper_params = []

    for feature_fraction in [0.25, 0.5, 0.75, 0.95]:
        max_depth = 10
        for num_of_trees in [5, 10, 15, 20]:
            list_hyper_params.append((num_of_trees, max_depth, feature_fraction))

    returnedDic = {}
    returnedDic["detail"] = {}
    returnedDic["detail"]["indeces"] = []

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
                 stage_name: {
                     stageTimeStr: end_time - start_time,
                     executeTimeStr: exe_time, interactTimeStr: interact_time,
                     serializeTimeStr: seri_time, deserializeTimeStr: desei_time
                 },
                 "key1": "inv_300", "num_of_trees": num_of_trees, "max_depth": max_depth,
                 "feature_fraction": feature_fraction, "threads": 6, "start_tick": start_time,
                 "leave_tick": cur_tick_ms()}
            num_of_trees = []
            max_depth = []
            feature_fraction = []
            returnedDic["detail"]["indeces"].append(j)

    print(returnedDic)
    return returnedDic


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
        start_process = int(round(time.time() * 1000))
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
        end_process = int(round(time.time() * 1000))

        model_name = "lightGBM_model_" + str(_id) + ".txt"
        save_path = "tmp/" + model_name

        print("Ready to uploaded " + model_name)
        start_upload = int(round(time.time() * 1000))
        gbm.save_model(save_path)
        s3_client.fput_object(bucket_name, "ML_Pipeline/" + model_name, save_path)
        end_upload = int(round(time.time() * 1000))
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

    id = int(os.environ.get("ID"))
    event = meta['detail']['indeces'][int(id)]
    network_time = cur_tick_ms() - event["leave_tick"]
    exe_time = 0
    interact_time = 0
    seri_time = 0
    desei_time = 0

    start_time = cur_tick_ms()

    # TODO: download from external
    filename = "tmp/Digits_Train_Transform.txt"
    tick = cur_tick_ms()
    s3_client.fget_object(bucket_name, 'ML_Pipeline/train_pca_transform_2.txt', filename)
    interact_time += cur_tick_ms() - tick

    tick = cur_tick_ms()
    train_data = np.genfromtxt(filename, delimiter='\t')
    desei_time += cur_tick_ms() - tick

    y_train = train_data[0:5000, 0]
    X_train = train_data[0:5000, 1:train_data.shape[1]]
    # lgb_train = lgb.Dataset(X_train, y_train)

    # print(type(y_train))
    # print(type(lgb_train))
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
    exe_time += sum(process_dict.values())
    interact_time += sum(upload_dict.values())
    j = {
        'statusCode': 200,
        'trees_max_depthes': return_dict.keys(),
        'accuracies': return_dict.values(),
        'PCA': event['PCA'],
        'Train': {
            stageTimeStr: (end_time - start_time),
            executeTimeStr: exe_time, interactTimeStr: interact_time,
            serializeTimeStr: seri_time, deserializeTimeStr: desei_time,
            'upload_model_time': upload_dict.values(), 'train_process_time': process_dict.values()
        },
        'start_tick': event['start_tick'],
        'leave_tick': end_time,
        networkTimeStr: network_time
    }
    print(j)
    return j


def reduce(meta):
    meta[networkTimeStr] = cur_tick_ms() - meta['leave_tick'] + int(meta[networkTimeStr])
    event = [meta]
    configs_list = []
    accuracy_list = []
    for i in range(len(event)):
        print(event[i])
        for j in range(len(event[i]["trees_max_depthes"])):
            configs_list.append(event[i]["trees_max_depthes"][j])
            accuracy_list.append(event[i]["accuracies"][j])

    Z = [x for _, x in sorted(zip(accuracy_list, configs_list))]
    returned_configs = Z[-10:len(accuracy_list)]
    returned_latecy = sorted(accuracy_list)[-10:len(accuracy_list)]
    end_time = cur_tick_ms()
    e2e = end_time - meta['start_tick']
    ret = {
        'statusCode': 200,
        'accuracy': returned_configs,
        'returned_latency': returned_latecy,
        'profile': {
            'PCA': meta['PCA'],
            'Train': meta['Train'],
            networkTimeStr: meta[networkTimeStr],
            'e2e_ms': e2e,
        },
    }
    return ret


if __name__ == '__main__':
    res = splitter({})
