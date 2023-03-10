import numpy as np
from numpy.linalg import eig

from util import cur_tick_ms


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


if __name__ == '__main__':
    train_data = np.genfromtxt('dataset/Digits_Train.txt', delimiter='\t')
    execute_start_time = cur_tick_ms()
    vectors, first_n_A_label = execute_body(train_data)
    execute_end_time = cur_tick_ms()
    print(f'exe time {execute_end_time - execute_start_time}')
