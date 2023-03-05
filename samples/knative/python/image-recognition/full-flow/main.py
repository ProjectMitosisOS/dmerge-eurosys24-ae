import json
import os
import time

from PIL import ImageFile
from imageai.Detection import ObjectDetection
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
    detector = ObjectDetection()
    model_path = "models/yolo-tiny.h5"

    start_time = cur_tick_ms()
    rela_path = input_file.split('/')[-1]
    output_path = "out/output_" + rela_path
    detector.setModelTypeAsTinyYOLOv3()

    detector.setModelPath(model_path)
    detector.loadModel()
    filename = input_file

    detection = detector.detectObjectsFromImage(
        input_image=filename,
        output_image_path=output_path,
        minimum_percentage_probability=40)
    detect_time = cur_tick_ms() - start_time

    tick = cur_tick_ms()
    li = json.dumps(detection)
    json_seri_time = cur_tick_ms() - tick

    for box in range(len(detection)):
        print(detection[box])

    dic = {
        'detect_time': detect_time,
        'json': json_seri_time
    }
    print(dic)
    return dic


if __name__ == '__main__':
    detect_object(input_file='images/val2017/000000000139.jpg')
