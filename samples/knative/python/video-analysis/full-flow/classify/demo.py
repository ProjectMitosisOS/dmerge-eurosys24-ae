import sys
from imageai.Detection import ObjectDetection
from multiprocessing import Process, Manager
import multiprocessing
import time
from minio import Minio
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageFile
import zipfile
import os

ImageFile.LOAD_TRUNCATED_IMAGES = True
s3_classfier_client = Minio(
    endpoint='127.0.0.1:9000',
    secure=False,
    access_key='wSgN80XAPlP5tLgD', secret_key='z9YsQtR2QENolHcM4mrqWLPSYiJBoa7W')
bucket_name = 'video-analysis'
if not s3_classfier_client.bucket_exists(bucket_name):
    s3_classfier_client.make_bucket(bucket_name)


def cur_tick_ms():
    return int(round(time.time() * 1000))


def delete_tmp():
    for root, dirs, files in os.walk("/tmp/", topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))


def detect_object():
    detector = ObjectDetection()
    model_path = "models/yolo-tiny.h5"

    start_time = cur_tick_ms()

    output_path = "images/output_" + str(5) + ".jpg"
    detector.setModelTypeAsTinyYOLOv3()

    detector.setModelPath(model_path)
    detector.loadModel()
    filename = 'images/input_slow.jpg'

    detection = detector.detectObjectsFromImage(
        input_image=filename,
        output_image_path=output_path,
        minimum_percentage_probability=50)

    for box in range(len(detection)):
        print(detection[box])


if __name__ == '__main__':
    detect_object()
