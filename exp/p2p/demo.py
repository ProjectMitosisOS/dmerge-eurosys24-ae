import copy
import numpy as np
import uuid
import os
from util import cur_tick_ms
from numpy.linalg import eig

data_path = 'data/digits.txt'
train_data = np.genfromtxt(data_path, delimiter='\t')
exe_time = 0
start = cur_tick_ms()
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
exe_time = cur_tick_ms() - start

print(f'passed {exe_time} ms')
