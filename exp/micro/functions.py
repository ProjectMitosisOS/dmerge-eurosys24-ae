import logging
import os
import pickle
import threading
import uuid
import array

import requests
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
    loop = int(meta.get('loop', '0'))
    return {
        'status': 200,
        'wf_id': str(uuid.uuid4()),
        'features': {
            'protocol': os.environ.get('PROTOCOL', 'S3')  # value of DMERGE / S3 / RPC --- Default as S3
        },
        'profile': {
            'loop': loop,
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

global_obj = {}

payload_size = int(os.environ.get('PAYLOAD_SIZE', 4096))


def producer(meta):
    stage_name = 'producer'
    list_length = payload_size // 8
    data = [0] * list_length

    # data = lgb.Booster(model_file='data/mnist_model.txt')

    def producer_es(_meta):
        filename = "/tmp/data.txt"
        out_meta = _meta
        tick = cur_tick_ms()
        o = pickle.dumps(data)
        out_meta['profile']['sd_bytes_len'] += len(o)
        sd_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        s3_obj_key = 'Data-{}.txt'.format(util.random_string())
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
        out_meta['payload'] = data
        sd_time = cur_tick_ms() - tick

        out_meta['profile'].update({
            'producer': {
                'sd_time': sd_time,
            },
        })
        return out_meta

    def producer_dmerge(_meta):
        out_meta = _meta
        o = data

        tick = cur_tick_ms()
        global_obj['data'] = o  # write to global variable to avoid GC

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
        app_logger.debug(f'DMERGE profile: {out_meta["profile"]}')
        return out_meta

    wf_start_tick = cur_tick_ms()
    producer_dispatcher = {
        'ES': producer_es,
        'DMERGE': producer_dmerge,
        'DMERGE_PUSH': producer_dmerge,
        'RPC': producer_rpc
    }
    dispatch_key = meta['features']['protocol']
    out_dict = producer_dispatcher[dispatch_key](meta)
    out_dict['profile']['leave_tick'] = cur_tick_ms()
    out_dict['profile']['wf_start_tick'] = wf_start_tick
    out_dict['profile'][stage_name]['stage_time'] = sum(out_dict['profile'][stage_name].values())
    return out_dict


def consumer(event):
    stage_name = 'consumer'

    def consumer_es(event):
        out_meta = event

        tick = cur_tick_ms()
        s3_obj_key = event['s3_obj_key']
        o = util.redis_get(s3_obj_key)
        es_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        data = pickle.loads(o)
        sd_time = cur_tick_ms() - tick

        out_meta['profile'].update({
            'consumer': {
                'es_time': es_time,
                'sd_time': sd_time,
            },
        })
        app_logger.debug(f'S3 profile: {out_meta["profile"]}')
        return out_meta

    def consumer_rpc(_event):
        tick = util.cur_tick_us()
        _data = np.array(event['payload'])
        sum_val = sum(_data)
        sd_time = util.cur_tick_us() - tick

        event.pop('payload')
        out_meta = event
        out_meta['profile'].update({
            'consumer': {
                'sd_time': sd_time / 1000,
            },
        })
        app_logger.debug(f'RPC profile: {out_meta["profile"]}')
        fetch_time = sd_time + event["profile"]["runtime"]["fetch_data_time"] * 1000
        app_logger.info(f'RPC transfer {payload_size / 1024}K data cost {fetch_time} us')
        return out_meta

    def consumer_dmerge(event):
        out_meta = event
        target_id = event['obj_hash']['data']
        route = event['route']
        gid, mac_id, hint, nic_id = route['gid'], route['machine_id'], \
            route['hint'], route['nic_id']

        pull_start_time = cur_tick_ms()
        r = util.pull(mac_id, hint)
        assert r == 0
        _data = util.fetch(target_id)  # Retrieve all or not
        pull_time = cur_tick_ms() - pull_start_time
        fetch_start_tick = util.cur_tick_us()
        sum_val = sum(_data)
        fetch_time = util.cur_tick_us() - fetch_start_tick
        out_meta['profile'].update({
            'consumer': {
                'pull_time': pull_time,
            },
        })
        app_logger.info(f'DMerge transfer {payload_size / 1024}K data cost {fetch_time} us')

        app_logger.debug(f'DMERGE profile: {out_meta["profile"]}')
        return out_meta

    consumer_dispatcher = {
        'ES': consumer_es,
        'DMERGE': consumer_dmerge,
        'DMERGE_PUSH': consumer_dmerge,
        'RPC': consumer_rpc
    }
    dispatch_key = event['features']['protocol']
    out_dict = consumer_dispatcher[dispatch_key](event)
    out_dict['profile']['wf_end_tick'] = cur_tick_ms()
    out_dict['profile']['leave_tick'] = cur_tick_ms()
    out_dict['profile'][stage_name]['stage_time'] = sum(out_dict['profile'][stage_name].values())
    return out_dict


def sink(metas):
    def send_request(data):
        headers = {
            'Ce-Id': '536808d3-88be-4077-9d7a-a3f162705f79',
            'Ce-Specversion': '1.0',
            'Ce-Type': 'dev.knative.sources.ping',
            'Ce-Source': 'ping-pong',
            'Content-Type': 'application/json'
        }
        response = requests.post(
            'http://broker-ingress.knative-eventing.svc.cluster.local/default/default-broker',
            headers=headers,
            json=data
        )

    for i, meta in enumerate(metas):
        app_logger.debug(f"@{i}:[ {util.PROTOCOL} ] "
                         f"whole profile: {meta['profile']}")
    meta = metas[-1]
    loop = meta['profile']['loop']
    app_logger.info(f"[ {util.PROTOCOL} ] "
                    f"whole profile: {meta['profile']}")
    meta['profile']['runtime']['stage_time'] = sum(meta['profile']['runtime'].values())

    reduced_profile = util.reduce_profile(meta['profile'])
    e2e_time = meta['profile']['wf_end_tick'] - meta['profile']['wf_start_tick']
    # app_logger.info(f"[ {util.PROTOCOL} ] "
    #                         f"workflow e2e time for whole: {e2e_time}")
    app_logger.info(f"[ {util.PROTOCOL} ] "
                    f"[{loop}] workflow e2e time: {reduced_profile['stage_time']}")
    for k, v in reduced_profile.items():
        app_logger.info(f"Part@ {k} passed {v} ms")
    app_logger.info(f"Part@ cur_tick_ms passed {cur_tick_ms()} ms")
    if loop > 0:
        loop -= 1
        thread = threading.Thread(target=send_request, args=({'loop': loop},))
        thread.start()
    return {}


def default_handler(meta):
    app_logger.error(f'[default_handler] not a default path for type')
    return meta


if __name__ == '__main__':
    res = producer({})
