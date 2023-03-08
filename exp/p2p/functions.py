import copy

from minio import Minio
import uuid
import os
from flask import current_app

s3_client = Minio(
    endpoint='minio:9000',
    secure=False,
    access_key='ACCESS_KEY', secret_key='SECRET_KEY')
bucket_name = 'p2p'

if not s3_client.bucket_exists(bucket_name):
    s3_client.make_bucket(bucket_name)


# Profile is seperated into 4 parts as below:
# @Execution: Normal data process
# @Interaction with external resources: Current is Redis KV
# @Serialize: Data transform into IR
# @Deserialize: IR transform into Data

def read_lines(path):
    with open(path) as f:
        return f.readlines()


stageTimeStr = 'stage_time'
executeTimeStr = 'execute_time'
interactTimeStr = 'interact_time'
serializeTimeStr = 'serialize_time'
deserializeTimeStr = 'deserialize_time'
networkTimeStr = 'network_time'


def splitter(meta):
    current_app.logger.debug(f'splitter, {meta}')
    return {
        'status': 200
    }


def producer(meta):
    current_app.logger.debug(f'producer, {meta}')
    out_meta = meta

    return out_meta


def consumer(metas):
    stage = 'consumer'
    current_app.logger.debug(f'hello world, {metas}')
    return metas[-1] if len(metas) > 0 else 0


if __name__ == '__main__':
    res = producer({})
