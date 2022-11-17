#!/usr/bin/env python
import os
import json
import subprocess
import re
import time

FFMPEG_STATIC = "var/ffmpeg"

length_regexp = 'Duration: (\d{2}):(\d{2}):(\d{2})\.\d+,'
re_length = re.compile(length_regexp)


def lambda_handler(event, src_video=0):
    video_file_path = '../dataset/min_{}.mp4'.format(str(src_video))

    filename = video_file_path
    f = open(filename, "wb")
    print(event)
    src_video = event['src_name']
    DOP = int(event['DOP'])
    detect_prob = int(event['detect_prob'])
    # s3_client.download_fileobj(bucket_name, "Video_Src/min_" + src_video + ".mp4", f, Config=config)
    f.close()

    # Read file content
    output = subprocess.Popen(FFMPEG_STATIC + " -i '" + filename + "' 2>&1 | grep 'Duration'",
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
        print("Video length in seconds: " + str(video_length))

        start = 0
        chunk_size = 2  # in seconds
        while (start < video_length):
            end = min(video_length - start, chunk_size)
            millis = int(round(time.time() * 1000))
            millis_list.append(millis)
            chunk_video_name = 'min_' + src_video + "_" + str(count) + "_" + str(millis) + '.mp4'
            subprocess.call([FFMPEG_STATIC, '-i', filename, '-ss', str(start), '-t', str(end), '-c', 'copy',
                             '/tmp/' + chunk_video_name])

            count = count + 1
            start = start + chunk_size
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
            tempDic['detect_prob'] = detect_prob
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
