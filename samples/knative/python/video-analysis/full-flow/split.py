#!/usr/bin/env python
import os
import json
import subprocess
import re
import time

from minio import Minio

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
    filename = '../dataset/min_{}.mp4'.format(str(src_video))
    s3_client.fput_object(bucketName, "Video_Src/min_" + src_video + ".mp4", filename)


def lambda_handler(src_video=0, partition_num=2):
    """
    Each video with length 60s, split into chunks with 2s length.
    Thus, we have 30 chunks overall. And we can further partition these 30 chunks into `partition_num`
    :param src_video: source video ID. See resources in `dataset`
    :param partition_num: Partition number. It should be the factor of `30` (e.g. 1, 3, 5, 6, 15, 30)
    :return: A list of the events with length of `partition_num`
    """
    filename = "/tmp/src.mp4"
    s3_client.fget_object(bucketName, "Video_Src/min_" + str(src_video) + ".mp4", filename)
    command = FFMPEG_STATIC + " -i '" + filename + "' 2>&1 | grep 'Duration'"
    # factor of 30
    DOP = partition_num
    print('command:', command)
    output = subprocess.Popen(command,
                              shell=True,
                              stdout=subprocess.PIPE
                              ).stdout.read().decode("utf-8")

    print(output)

    matches = re_length.search(output)
    count = 0
    millis_list = []
    if matches:
        video_length = int(matches.group(1)) * 3600 + \
                       int(matches.group(2)) * 60 + \
                       int(matches.group(3))
        print("Video length in seconds: " + str(video_length))  # 60s

        start = 0
        chunk_size = 2  # in seconds
        while start < video_length:
            end = min(video_length - start, chunk_size)
            millis = int(round(time.time() * 1000))
            millis_list.append(millis)
            chunk_video_name = 'min_' + str(src_video) + "_" + str(count) + "_" + str(millis) + '.mp4'
            subprocess.call([FFMPEG_STATIC, '-i', filename, '-ss', str(start), '-t', str(end), '-c', 'copy',
                             '/tmp/' + chunk_video_name])

            count = count + 1
            start = start + chunk_size
            s3_client.fput_object(bucketName,
                                  "Video_Chunks_Step/" + chunk_video_name,
                                  "/tmp/" + chunk_video_name,
                                  )
    print("Done!")

    payload = count / DOP
    listOfDics = []
    currentList = []
    currentMillis = []
    for i in range(count):
        if len(currentList) < payload:
            currentList.append(i)
            currentMillis.append(millis_list[i])
        if len(currentList) == payload:
            tempDic = {}
            tempDic['values'] = currentList
            tempDic['source_id'] = src_video
            tempDic['millis'] = currentMillis
            listOfDics.append(tempDic)
            currentList = []
            currentMillis = []

    returnedObj = {
        "detail": {
            "indeces": listOfDics
        }
    }
    print(returnedObj)
    return returnedObj
