import os

from redis_client import *
import numpy as np
from numpy.linalg import eig
import time
import lightgbm as lgb
import numpy as np
import json
import random
import os
from multiprocessing import Process, Manager

test_data_file_path = 'dataset/Digits_Test.txt'
train_data_file_path = 'dataset/Digits_Train.txt'

# Dump before running
dump_file_to_kv(train_data_file_path)
dump_file_to_kv(test_data_file_path)


def splitter(meta):
    out_data = meta.copy()

    mapper_num = 2 if 'mapper_num' not in dict(meta).keys() else int(meta['mapper_num'])

    start_time = int(round(time.time() * 1000))
    start_download = int(round(time.time() * 1000))
    train_data = np.genfromtxt(read_file_from_kv(train_data_file_path))
    end_download = int(round(time.time() * 1000))
    """
    Start Execution
    """
    print('finish download')
    start_process = int(round(time.time() * 1000))
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

    np.savetxt("tmp/vectors_pca.txt", vectors, delimiter="\t")
    first_n_A = PA.T[:, 0:100].real
    train_labels = train_labels.reshape(train_labels.shape[0], 1)
    first_n_A_label = np.concatenate((train_labels, first_n_A), axis=1)
    np.savetxt("tmp/Digits_Train_Transform.txt", first_n_A_label, delimiter="\t")
    end_process = int(round(time.time() * 1000))

    start_upload = int(round(time.time() * 1000))
    ## TODO: Upload to external
    dump_file_to_kv('tmp/vectors_pca.txt')
    dump_file_to_kv('tmp/Digits_Train_Transform.txt')
    ##  s3_client.upload_file("/tmp/vectors_pca.txt.npy", bucket_name, "ML_Pipeline/vectors_pca.txt", Config=config)
    ## s3_client.upload_file("/tmp/Digits_Train_Transform.txt", bucket_name, "ML_Pipeline/train_pca_transform_2.txt", Config=config)

    end_upload = int(round(time.time() * 1000))
    """
    End Execution
    """
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
            j = {"mod_index": num_bundles, "PCA_Download": (end_download - start_download),
                 "PCA_Process": (end_process - start_process), "PCA_Upload": (end_upload - start_upload),
                 "key1": "inv_300", "num_of_trees": num_of_trees, "max_depth": max_depth,
                 "feature_fraction": feature_fraction, "threads": 6, "start_tick": start_time}
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
        # TODO: Upload
        gbm.save_model(save_path)
        # s3_client.upload_file("/tmp/" + model_name, bucket_name, "ML_Pipeline/" + model_name, Config=config)
        # dump_file_to_kv(save_path)
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

    start_time = int(round(time.time() * 1000))

    start_download = int(round(time.time() * 1000))
    # TODO: download from external
    filename = "tmp/Digits_Train_Transform.txt"
    train_data = np.genfromtxt(read_file_from_kv(filename), delimiter='\t')
    # train_data = np.genfromtxt(filename, delimiter='\t')
    end_download = int(round(time.time() * 1000))

    start_process = int(round(time.time() * 1000))

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

    end_process = int(round(time.time() * 1000))
    end_time = int(round(time.time() * 1000))
    e2e = end_time - start_time
    print("download duration: " + str(end_time - start_time))
    print("E2E duration: " + str(e2e))
    j = {
        'statusCode': 200,
        'body': json.dumps('Done Training Threads = ' + str(threads)),
        'key1': event['key1'],
        'duration': e2e,
        'trees_max_depthes': return_dict.keys(),
        'accuracies': return_dict.values(),
        'process_times': process_dict.values(),
        'upload_times': upload_dict.values(),
        'download_times': (end_download - start_download),
        'PCA_Download': event['PCA_Download'],
        'PCA_Process': event['PCA_Process'],
        'PCA_Upload': event['PCA_Upload'],
        'start_tick': event['start_tick']
    }
    print(j)
    return j


def reduce(meta):
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
    end_time = int(round(time.time() * 1000))
    e2e = end_time - meta['start_tick']
    return {
        'statusCode': 200,
        'accuracy': returned_configs,
        'returned_latecy': returned_latecy,
        'all_data': event,
        'e2e_ms': e2e
    }


if __name__ == '__main__':
    res = splitter({})
    pass
