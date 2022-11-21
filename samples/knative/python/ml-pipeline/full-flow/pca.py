import json
from numpy import genfromtxt
import numpy as np
from numpy.linalg import eig
import random
import time
from util import dump_file_to_kv

test_data_file_path = '../dataset/Digits_Test.txt'
train_data_file_path = '../dataset/Digits_Train.txt'


def PCA(partition_num=16):
    content = dump_file_to_kv(train_data_file_path)
    train_data = genfromtxt(json.loads(content))

    print('finish download')
    start_time = int(round(time.time() * 1000))
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

    np.save("/tmp/vectors_pca.txt", vectors)
    first_n_A = PA.T[:, 0:100].real
    train_labels = train_labels.reshape(train_labels.shape[0], 1)
    first_n_A_label = np.concatenate((train_labels, first_n_A), axis=1)

    PCA_file_name = "/tmp/Digits_Train_Transform.txt"
    np.savetxt(PCA_file_name, first_n_A_label, delimiter="\t")
    ###########################
    end_time = int(round(time.time() * 1000))

    ### Construct return params
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
    bundle_size = len(list_hyper_params) / partition_num
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
                 "feature_fraction": feature_fraction, "threads": 6}
            num_of_trees = []
            max_depth = []
            feature_fraction = []
            returnedDic["detail"]["indeces"].append(j)

    # print(returnedDic)
    return PCA_file_name, returnedDic
