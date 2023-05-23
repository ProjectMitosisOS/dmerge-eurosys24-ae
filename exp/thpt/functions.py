import logging
import os
import pickle
import time
import uuid

from bindings import *

import util
from util import cur_tick_ms

app_logger = logging.getLogger('app_logger')


# Profile is seperated into 4 parts as below:
# @Execution: Normal data process
# @Interaction with external resources: Current is Redis KV
# @Serialize: Data transform into IR
# @Deserialize: IR transform into Data

def splitter(meta):
    return {
        'status': 200,
        'wf_id': str(uuid.uuid4()),
        'features': {
            'protocol': os.environ.get('PROTOCOL', 'S3')  # value of DMERGE / S3 / RPC --- Default as S3
        },
        'profile': {
            'sd_bytes_len': 0,
            'leave_tick': cur_tick_ms(),
            'runtime': {
                'fetch_data_time': 0,
                'sd_time': 0,
                'nt_time': 0,
            }
        },

    }


import numpy as np
import lightgbm as lgb

global_obj = {}

target_data = np.genfromtxt('data/Digits_Train.txt', delimiter='\t')
touch_len = int(len(target_data) * int(os.environ.get('TOUCH_RATIO', 100)) / 100)
target_data = target_data[:touch_len]
# target_data = lgb.Booster(model_file='data/mnist_model.txt')
# with open('data/article.txt') as f:
#     lines = f.readlines()
# target_data = lines
target_data_o = pickle.dumps(target_data)


def producer(meta):
    stage_name = 'producer'

    def producer_es(_meta):
        filename = "/tmp/data.txt"
        out_meta = _meta
        tick = cur_tick_ms()
        o = pickle.dumps(target_data)
        sd_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        s3_obj_key = 'obj.txt'
        util.redis_put(s3_obj_key, o)
        es_time = cur_tick_ms() - tick

        out_meta['s3_obj_key'] = s3_obj_key
        out_meta['profile'].update({
            'producer': {
                'es_time': es_time,
                'sd_time': sd_time,
            },
        })
        return out_meta

    def producer_rpc(_meta):
        out_meta = _meta

        tick = cur_tick_ms()
        out_meta['payload'] = {
            # 'model': model,
            'arr': target_data,
        }
        sd_time = cur_tick_ms() - tick

        out_meta['profile'].update({
            'producer': {
                'sd_time': sd_time,
            },
        })
        return out_meta

    def producer_dmerge(_meta):
        out_meta = _meta
        o = target_data
        tick = cur_tick_ms()
        global_obj['data'] = o  # write to global variable to avoid GC
        if util.PROTOCOL == 'ESRDMA':
            o = pickle.dumps(target_data)
            pickle.loads(o)
            # pickle.loads(pickle.dumps(model))
        addr = int(os.environ.get('BASE_HEX', '100000000'), 16)
        execute_time = cur_tick_ms() - tick

        push_start_time = cur_tick_ms()
        nic_idx = 0
        gid, mac_id, hint = util.push(nic_id=nic_idx, peak_addr=addr)
        if util.PROTOCOL == 'DMERGE_PUSH':
            util.push(nic_id=nic_idx, peak_addr=addr)
        push_time = cur_tick_ms() - push_start_time

        obj_id = id(global_obj["data"])

        out_meta['profile'].update({
            'producer': {
                'push_time': push_time,
                'execute_time': execute_time,
            },
        })
        out_meta['obj_hash'] = {
            'data': obj_id
        }
        out_meta['route'] = {
            'gid': gid,
            'machine_id': mac_id,
            'nic_id': nic_idx,
            'hint': hint
        }
        return out_meta

    producer_dispatcher = {
        'ES': producer_es,
        'DMERGE': producer_dmerge,
        'MITOSIS': producer_dmerge,
        'DMERGE_PUSH': producer_dmerge,
        'ESRDMA': producer_dmerge,
        'RPC': producer_rpc
    }
    dispatch_key = meta['features']['protocol']
    out_dict = producer_dispatcher[dispatch_key](meta)
    return out_dict


def consumer(event):
    stage_name = 'consumer'

    def consumer_es(event):
        out_meta = event

        tick = cur_tick_ms()
        s3_obj_key = event['s3_obj_key']
        try:
            o = util.redis_get(s3_obj_key)
        except:
            pass
        es_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        data = pickle.loads(target_data_o)
        sd_time = cur_tick_ms() - tick

        out_meta['profile'].update({
            'consumer': {
                'es_time': es_time,
                'sd_time': sd_time,
            },
        })
        return out_meta

    def consumer_rpc(_event):
        tick = cur_tick_ms()
        d = event['payload']['arr']
        sd_time = cur_tick_ms() - tick

        event.pop('payload')
        out_meta = event
        out_meta['profile'].update({
            'consumer': {
                'sd_time': sd_time,
            },
        })
        return out_meta

    def consumer_dmerge(event):
        pull_start_time = cur_tick_ms()
        out_meta = event
        target_id = event['obj_hash']['data']
        route = event['route']
        gid, mac_id, hint, nic_id = route['gid'], route['machine_id'], \
            route['hint'], route['nic_id']
        time.sleep(0.006 if util.PROTOCOL == 'MITOSIS' else 0.002)
        # r = util.pull(mac_id, hint)
        # assert r == 0
        # _data = util.fetch(target_id)  # Retrieve all or not
        pull_time = cur_tick_ms() - pull_start_time

        out_meta['profile'].update({
            'consumer': {
                'pull_time': pull_time,
            },
        })
        return out_meta

    consumer_dispatcher = {
        'ES': consumer_es,
        'DMERGE': consumer_dmerge,
        'MITOSIS': consumer_dmerge,
        'DMERGE_PUSH': consumer_dmerge,
        'ESRDMA': consumer_dmerge,
        'RPC': consumer_rpc
    }
    dispatch_key = event['features']['protocol']
    out_dict = consumer_dispatcher[dispatch_key](event)
    app_logger.info(f'[{util.PROTOCOL}] profile: {out_dict["profile"]}')
    return out_dict


def default_handler(meta):
    app_logger.error(f'[default_handler] not a default path for type')
    return meta


if __name__ == '__main__':
    res = producer({})
