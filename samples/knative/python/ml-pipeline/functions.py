from redis_client import *
import numpy as np
from numpy.linalg import eig
import time

test_data_file_path = 'dataset/Digits_Test.txt'
train_data_file_path = 'dataset/Digits_Train.txt'

# Dump before running
dump_file_to_kv(train_data_file_path)
dump_file_to_kv(test_data_file_path)


def splitter(meta):
    out_data = meta.copy()

    train_data = np.genfromtxt(read_file_from_kv(train_data_file_path))
    """
    Start Execution
    """
    start_time = int(round(time.time() * 1000))
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
    """
    End Execution
    """
    end_time = int(round(time.time() * 1000))

    out_data['split/execution_ms'] = end_time - start_time
    out_data['key'] = train_data_file_path
    return out_data


def trainer(meta):
    out_data = meta.copy()
    return out_data


def reduce(meta):
    out_data = meta.copy()
    return out_data
