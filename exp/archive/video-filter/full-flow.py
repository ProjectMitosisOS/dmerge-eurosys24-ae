#!/usr/bin/env python
import re
import subprocess

import cv2
import numpy as np
from minio import Minio
import time


def cur_tick_ms():
    return int(round(time.time() * 1000))


s3_client = Minio(
    endpoint='127.0.0.1:9000',
    secure=False,
    access_key='wSgN80XAPlP5tLgD', secret_key='z9YsQtR2QENolHcM4mrqWLPSYiJBoa7W')
bucketName = 'video-analysis'
if not s3_client.bucket_exists(bucketName):
    s3_client.make_bucket(bucketName)

# FIXME: Change it into your ffmpeg path, and Don't put under $HOME path!
FFMPEG_STATIC = "ffmpeg"  # sudo apt-get install ffmpeg

length_regexp = 'Duration: (\d{2}):(\d{2}):(\d{2})\.\d+,'
re_length = re.compile(length_regexp)

for src_video in ['0', '1', '2', '3', '4', '5', '0909']:
    filename = './dataset/min_{}.mp4'.format(str(src_video))
    s3_client.fput_object(bucketName, "Video_Src/min_" + src_video + ".mp4", filename)


def split(src_video=0, partition_num=2):
    """
    Each video with length 60s, split into chunks with 2s length.
    Thus, we have 30 chunks overall. And we can further partition these 30 chunks into `partition_num`
    :param src_video: source video ID. See resources in `dataset`
    :param partition_num: Partition number. It should be the factor of `30` (e.g. 1, 3, 5, 6, 15, 30)
    :return: A list of the events with length of `partition_num`
    """
    filename = "out/src.mp4"
    s3_client.fget_object(bucketName, "Video_Src/min_" + str(src_video) + ".mp4", filename)
    command = FFMPEG_STATIC + " -i '" + filename + "' 2>&1 | grep 'Duration'"
    # factor of 30
    output = subprocess.Popen(command,
                              shell=True,
                              stdout=subprocess.PIPE
                              ).stdout.read().decode("utf-8")
    matches = re_length.search(output)
    s3_obj_keys = []
    s3_time = 0
    execute_time = 0

    if matches:
        video_length = int(matches.group(1)) * 3600 + \
                       int(matches.group(2)) * 60 + \
                       int(matches.group(3))
        step_second = video_length // partition_num
        start_second = 0
        chunk_count = 0
        while start_second < video_length:
            tick = cur_tick_ms()
            end_second = min(video_length - start_second, step_second)
            chunk_video_name = f'min_{str(src_video)}_{str(chunk_count)}_{str(start_second)}_{str(end_second)}.mp4'
            key = "Video_Chunks_Step/" + chunk_video_name
            chunk_file_name = "./out/" + chunk_video_name
            subprocess.call([FFMPEG_STATIC, '-y', '-i', filename, '-ss', str(start_second), '-t',
                             str(end_second), '-c', 'copy',
                             chunk_file_name])
            chunk_count += 1
            start_second += step_second
            execute_time += cur_tick_ms() - tick

            tick = cur_tick_ms()
            s3_client.fput_object(bucketName, key, chunk_file_name)
            s3_time += cur_tick_ms() - tick
            s3_obj_keys.append(key)
    print(f"Done! key is {s3_obj_keys}")
    out_dict = {
        's3_obj_keys': s3_obj_keys,
        'profile': {
            'split': {
                's3_time': s3_time,
                'execute_time': execute_time
            }
        }
    }
    return out_dict


def video_filter(event):
    """
    ffmpeg -i input.mp4 -vf hue=s=0 -c:a copy output.mp4
    :param event:
    :return:
    """
    ID = 3
    key = event['s3_obj_keys'][ID]
    local_file_path = 'out/work.mp4'
    out_file_path = 'out/output.mp4'
    s3_client.fget_object(bucketName, key, local_file_path)
    subprocess.call([FFMPEG_STATIC, '-y', '-i', local_file_path, '-vf', 'hue=s=0', '-c:a', 'copy', out_file_path])
    # Open the video file
    tick = cur_tick_ms()
    cap = cv2.VideoCapture(out_file_path)
    frameCount = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frameWidth = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frameHeight = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    buf = np.empty((frameCount, frameHeight, frameWidth, 3), np.dtype('uint8'))
    fc = 0
    ret = True
    while fc < frameCount and ret:
        ret, buf[fc] = cap.read()
        fc += 1
    cap.release()
    cv2.waitKey(0)
    print(f'time passed {cur_tick_ms() - tick} ms. Dict: {event["profile"]}')


if __name__ == '__main__':
    event = split(0, 10)
    video_filter(event)
