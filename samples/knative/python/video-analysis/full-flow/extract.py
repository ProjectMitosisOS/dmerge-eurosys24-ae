#!/usr/bin/env python
import json
import subprocess
import time

from minio import Minio

# FIXME: Change it into your ffmpeg path, and Don't put under $HOME path!
FFMPEG_STATIC = "ffmpeg"
s3_client = Minio(
    endpoint='127.0.0.1:9000',
    secure=False,
    access_key='wSgN80XAPlP5tLgD', secret_key='z9YsQtR2QENolHcM4mrqWLPSYiJBoa7W')
bucketName = 'video-analysis'
if not s3_client.bucket_exists(bucketName):
    s3_client.make_bucket(bucketName)


def lambda_handler(event):
    # print(subprocess.call([FFMPEG_STATIC]))
    print(event)
    list_of_chunks = event['values']
    src_video = event['source_id']
    millis_list = event['millis']
    count = 0
    extract_millis = []

    for record in list_of_chunks:
        filename = "/tmp/chunk_" + str(record) + ".mp4"
        key = "Video_Chunks_Step/min_" + str(src_video)
        key = key + "_" + str(record) + "_"
        key = key + str(millis_list[count]) + ".mp4"

        count = count + 1

        s3_client.fget_object(bucketName, key, filename)

        millis = int(round(time.time() * 1000))
        extract_millis.append(millis)

        frame_name = key.replace("Video_Chunks_Step/", "").replace("min", "frame").replace(".mp4",
                                                                                           "_" + str(millis) + ".jpg")
        subprocess.call([FFMPEG_STATIC, '-i', filename, '-frames:v', "1", "-q:v", "1", '/tmp/' + frame_name])
        try:
            s3_client.fput_object(bucketName, "Video_Frames_Step/" + frame_name, "/tmp/" + frame_name)
        except:
            s3_client.fput_object(bucketName, "Video_Frames_Step/" + frame_name, "var/Frame_1.jpg")
    print("Extract Done!")

    obj = {
        'statusCode': 200,
        'counter': count,
        'millis1': millis_list,
        'millis2': extract_millis,
        'source_id': src_video,
        'values': list_of_chunks,
        'body': json.dumps('Download/Split/Upload Successful!'),

    }
    print(obj)
    return obj
