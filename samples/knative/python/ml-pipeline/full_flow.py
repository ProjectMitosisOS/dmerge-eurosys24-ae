import json
from numpy import genfromtxt
import numpy as np
from numpy.linalg import eig
import random
import time

test_data_file_path = 'dataset/Digits_Test.txt'
train_data_file_path = 'dataset/Digits_Train.txt'


def dump_file_to_kv(path):
    with open(path) as f:
        content = json.dumps(f.readlines())
        return content


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
np.savetxt("/tmp/Digits_Train_Transform.txt", first_n_A_label, delimiter="\t")
###########################
end_time = int(round(time.time() * 1000))

print("run %d ms" % (end_time - start_time))
