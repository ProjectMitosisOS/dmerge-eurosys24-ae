import os
import uuid

import numpy as np
from bindings import *
from flask import current_app
from minio import Minio
import lightgbm as lgb
import util
from util import cur_tick_ms

global_obj = {}

s3_client = Minio(
    endpoint='minio:9000',
    secure=False,
    access_key='ACCESS_KEY', secret_key='SECRET_KEY')
bucket_name = 'finra'
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


def accuracy_score(y_true, y_pred):
    correct = 0
    for i in range(len(y_true)):
        if y_true[i] == y_pred[i]:
            correct += 1
    accuracy = correct / len(y_true)
    return accuracy


def fill_gid(gid):
    new_mac_id_parts = []
    for part in gid.split(":"):
        new_part = ":".join([str(hex(int(i, 16)))[2:].zfill(4) for i in part.split(".")])
        new_mac_id_parts.append(new_part)
    new_mac_id = ":".join(new_mac_id_parts)
    return new_mac_id


def source(meta):
    return {
        'name': 'source'
    }


def fetchData(meta):
    def fetch_market_data(meta):
        """
        Fetch public data
        :param meta:
        :return:
        """

    current_app.logger.info(f"in fetchData {meta}")
    return meta

    def fetch_portfolio_data(meta):
        """
        Fetch local-sensitive data
        :param meta:
        :return:
        """
        return meta

    return meta


def runAuditRule(meta):
    current_app.logger.info(f"in runAuditRule {meta}")
    return meta


def default_handler(meta):
    current_app.logger.info(f'not a default path for type')
    return meta
