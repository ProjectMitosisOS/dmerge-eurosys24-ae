import os
import pickle
import time

from PIL import ImageFile
from minio import Minio

ImageFile.LOAD_TRUNCATED_IMAGES = True

s3_client = Minio(
    endpoint='127.0.0.1:9000',
    secure=False,
    access_key='wSgN80XAPlP5tLgD', secret_key='z9YsQtR2QENolHcM4mrqWLPSYiJBoa7W')
bucket_name = 'image-recognition'


def cur_tick_ms():
    return int(round(time.time() * 1000))


def delete_tmp():
    for root, dirs, files in os.walk("/tmp/", topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))


def detect_object(input_file):
    import tensorflow as tf
    import numpy as np
    from PIL import Image
    tick = cur_tick_ms()
    s3_client.fput_object(bucket_name, 'sample', input_file)
    s3_client.fget_object(bucket_name, 'sample', input_file)
    next_tick = cur_tick_ms()
    print(next_tick - tick)

    model = tf.keras.models.load_model('models/yolo-tiny.h5')

    start_tick = cur_tick_ms()
    img = Image.open(input_file)
    img = img.resize((224, 224))
    img_array = np.array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    predictions = model.predict(img_array)
    end_tick = cur_tick_ms()
    execute_time = end_tick - start_tick

    start_tick = cur_tick_ms()
    pickle.dumps(predictions)
    end_tick = cur_tick_ms()
    load_time = end_tick - start_tick

    dic = {
        'execute_time': execute_time,
        'load_time': load_time
    }
    print(dic)


if __name__ == '__main__':
    detect_object(input_file='images/sample.jpg')
