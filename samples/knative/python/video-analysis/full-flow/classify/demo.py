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
# s3_client = Minio(
#     endpoint='127.0.0.1:9000',
#     secure=False,
#     access_key='wSgN80XAPlP5tLgD', secret_key='z9YsQtR2QENolHcM4mrqWLPSYiJBoa7W')
bucket_name = 'video-analysis'


def delete_tmp():
    for root, dirs, files in os.walk("/tmp/", topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))


def detect_object(index, index2, image, src_video, milli_1, milli_2, detect_prob):
    detector = ObjectDetection()
    model_path = "/Users/lufangming/Documents/repos/dmerge/samples/knative/python/video-analysis/full-flow/classify/models/yolo-tiny.h5"

    start_time = int(round(time.time() * 1000))

    worker_dir = "/tmp/" + "Worker_" + str(index)
    if not os.path.exists(worker_dir):
        os.mkdir(worker_dir)

    filename = worker_dir + "/image_" + str(index) + ".jpg"
    key = image
    # s3_client.fget_object(bucket_name, key, filename)
    print("Download duration: " + str(time.time() * 1000 - start_time))
    # input_path = "~/images/input_fast.jpg"
    # if(index == 29):
    #   input_path = "~/images/input_slow.jpg"

    output_path = "images/output_" + str(index) + ".jpg"
    detector.setModelTypeAsTinyYOLOv3()

    detector.setModelPath(model_path)
    detector.loadModel()

    start_time = time.time() * 1000

    detection = detector.detectObjectsFromImage(input_image=filename, output_image_path=output_path,
                                                minimum_percentage_probability=detect_prob)

    for box in range(len(detection)):
        print(detection[box])

    if len(detection) > 10:
        original_image = Image.open(filename, mode='r')
        ths = []
        threads = 10
        start_index = 0
        step_size = int(len(detection) / threads) + 1

        for t in range(threads):
            end_index = min(start_index + step_size, len(detection))
            ths.append(Process(target=crop_and_sharpen,
                               args=(original_image.copy(), t, detection, start_index, end_index, worker_dir)))
            start_index = end_index
        for t in range(threads):
            ths[t].start()
        for t in range(threads):
            ths[t].join()
    millis_3 = int(round(time.time() * 1000))
    zipFileName = "detected_images_" + str(src_video) + "_" + str(index) + "_" + str(milli_1[0]) + "_" + str(
        milli_2[0]) + "_" + str(millis_3) + ".zip"
    myzip = zipfile.ZipFile("/tmp/" + zipFileName, 'w', zipfile.ZIP_DEFLATED)

    for f in os.listdir(worker_dir):
        myzip.write(worker_dir + "/" + f)

    # s3_client.fput_object(bucket_name, "Detected_Objects/" + zipFileName, "/tmp/" + zipFileName)
    print("file uploaded " + zipFileName)


def crop_and_sharpen(original_image, t, detection, start_index, end_index, worker_dir):
    for box in range(start_index, end_index):
        im_temp = original_image.crop((detection[box]['box_points'][0], detection[box]['box_points'][1],
                                       detection[box]['box_points'][2], detection[box]['box_points'][3]))
        im_resized = im_temp.resize((1408, 1408))
        im_resized_sharpened = im_resized.filter(ImageFilter.SHARPEN)
        fileName = worker_dir + "/" + detection[box]['name'] + "_" + str(box) + "_" + str(t) + "_" + ".jpg"
        im_resized_sharpened.save(fileName)
        # im_temp.save(fileName)

    # print(detection)
    print(len(detection))


def handler(event):
    start_time = int(round(time.time() * 1000))

    print(event)
    bucketName = bucket_name

    list_of_chunks = event['values']
    # list_of_images = event['images']

    print(list_of_chunks[0])
    src_video = event['source_id']
    millis_list1 = event['millis1']
    millis_list2 = event['millis2']
    detect_prob = 80  # from 0 to 100

    ths = []
    num_workers = len(list_of_chunks)
    for w in range(num_workers):
        key = "Video_Frames_Step/frame_" + str(src_video) + "_" + str(list_of_chunks[w]) + "_" + str(
                millis_list1[w]) + "_" + str(millis_list2[w]) + ".jpg"
        detect_object(list_of_chunks[w], list_of_chunks[w], key, src_video, millis_list1, millis_list2, detect_prob)
        # key = "Video_Frames_Step/frame_" + str(src_video) + "_" + str(list_of_chunks[w]) + "_" + str(
        #     millis_list1[w]) + "_" + str(millis_list2[w]) + ".jpg"
        # ths.append(Process(target=detect_object, args=(
        #     list_of_chunks[w], list_of_chunks[w], key, src_video, millis_list1, millis_list2, detect_prob)))

    # for t in range(num_workers):
    #     ths[t].start()
    # for t in range(num_workers):
    #     ths[t].join()

    end_time = time.time() * 1000
    diff_time = str(end_time - start_time)
    print("duration: " + diff_time)
    return {'duration': diff_time, 'values': str(event['values'])}

    # delete_tmp()


if __name__ == '__main__':
    pass
