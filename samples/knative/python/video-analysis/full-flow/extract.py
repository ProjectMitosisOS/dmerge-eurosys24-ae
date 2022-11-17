#!/usr/bin/env python
import json
import subprocess
import time

# FIXME: Change it into your ffmpeg path, and Don't put under $HOME path!
FFMPEG_STATIC = "/usr/local/bin/ffmpeg"


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
        f = open(filename, "wb")
        key = "../dataset/min_" + str(src_video)
        key = key + "_" + str(record) + "_"
        key = key + str(millis_list[count]) + ".mp4"

        count = count + 1

        # s3_client.download_fileobj(bucket_name, key, f, Config=config)
        f.close()
        millis = int(round(time.time() * 1000))
        extract_millis.append(millis)

        frame_name = key.replace("../dataset/", "").replace("min", "frame").replace(".mp4",
                                                                                           "_" + str(millis) + ".jpg")
        subprocess.call([FFMPEG_STATIC, '-i', filename, '-frames:v', "1", "-q:v", "1", '/tmp/' + frame_name])
        # try:
        #     s3_client.upload_file("/tmp/" + frame_name, bucket_name, "Video_Frames_Step/" + frame_name, Config=config)
        # except:
        #     s3_client.upload_file("var/Frame_1.jpg", bucket_name, "Video_Frames_Step/" + frame_name, Config=config)
    print("Done!")

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
