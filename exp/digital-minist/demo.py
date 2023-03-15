import time

import numpy as np
import lightgbm as lgb
from sklearn.metrics import accuracy_score


# Convert integer labels to one-hot encoded labels
def to_one_hot(labels, num_classes):
    return np.eye(num_classes)[labels]


def cur_tick_ms():
    return int(round(time.time() * 1000))


img_rows, img_cols = 28, 28
num_splits = 3
test_data = np.genfromtxt('dataset/Digits_Test.txt', delimiter='\t')

split_arr = np.array_split(test_data, num_splits)

tick = cur_tick_ms()
model = lgb.Booster(model_file='mnist_model.txt')
print(f'load model time: {cur_tick_ms() - tick}')

for i, data in enumerate(split_arr):
    print(f'Partition@{i} start !')
    y_test = data[:, 0]
    x_test = data[:, 1:data.shape[1]]

    tick = cur_tick_ms()
    y_pred = model.predict(x_test)
    y_pred = [np.argmax(line) for line in y_pred]

    # Evaluate the performance of the loaded model on the testing set
    accuracy = accuracy_score(y_test, y_pred)
    print('Loaded model accuracy:', accuracy)
    print(f'evaluate time: {cur_tick_ms() - tick}')

