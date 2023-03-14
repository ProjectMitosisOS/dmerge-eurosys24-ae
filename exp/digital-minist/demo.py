import time

import keras
import numpy as np
from keras.models import load_model


def cur_tick_ms():
    return int(round(time.time() * 1000))


model_path = 'cnn.h5'
img_rows, img_cols = 28, 28
num_splits = 3
test_data = np.genfromtxt('dataset/Digits_Test.txt', delimiter='\t')

split_arr = np.array_split(test_data, num_splits)

for i, data in enumerate(split_arr):
    print(f'Partition@{i} start !')
    y_test = data[:, 0]
    x_test = data[:, 1:data.shape[1]]

    tick = cur_tick_ms()
    y_test = keras.utils.to_categorical(y_test, 10)
    x_test = x_test.reshape(x_test.shape[0], img_rows, img_cols, 1)
    print(f'prepare time: {cur_tick_ms() - tick}')

    tick = cur_tick_ms()
    model = load_model(model_path)
    print(f'load model time: {cur_tick_ms() - tick}')

    tick = cur_tick_ms()
    score = model.evaluate(x_test, y_test, verbose=0)
    print(f'evaluate time: {cur_tick_ms() - tick}')

    print('Test loss:', score[0])
    print('Test accuracy:', score[1])
