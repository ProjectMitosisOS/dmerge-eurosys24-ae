#!/usr/bin/env python
import os
import json
import subprocess
import re
import time

# FIXME: Change it into your ffmpeg path, and Don't put under $HOME path!
FFMPEG_STATIC = "/usr/local/bin/ffmpeg"

length_regexp = 'Duration: (\d{2}):(\d{2}):(\d{2})\.\d+,'
re_length = re.compile(length_regexp)


def lambda_handler(src_video=0, partition_num=2):
    """
    Each video with length 60s, split into chunks with 2s length.
    Thus, we have 30 chunks overall. And we can further partition these 30 chunks into `partition_num`
    :param src_video: source video ID. See resources in `dataset`
    :param partition_num: Partition number. It should be the factor of `30` (e.g. 1, 3, 5, 6, 15, 30)
    :return: A list of the events with length of `partition_num`
    """
    filename = '../dataset/min_{}.mp4'.format(str(src_video))
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
            # TODO: Add to external storage!
            # s3_client.upload_file("/tmp/" + chunk_video_name, bucket_name, "Video_Chunks_Step/" + chunk_video_name,
            #                       Config=config)
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
