import os
import pickle
import uuid

from bindings import *
from flask import current_app
from minio import Minio
import lightgbm as lgb
import util
import json
import numpy as np

from util import cur_tick_ms


class NumpyJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, bytes):
            return str(obj, encoding='utf-8')
        return json.JSONEncoder.default(self, obj)


global_obj = {}

s3_client = Minio(
    endpoint='minio:9000',
    secure=False,
    access_key='ACCESS_KEY', secret_key='SECRET_KEY')
bucket_name = 'digital-minist'
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


def splitter(meta):
    test_data = np.genfromtxt('dataset/Digits_Test.txt', delimiter='\t')
    wf_start_tick = cur_tick_ms()
    tick = cur_tick_ms()
    predict_worker_num = int(os.environ.get('WORKER_NUM', '1'))
    split_arr = np.array_split(test_data, predict_worker_num)
    model = lgb.Booster(model_file='mnist_model.txt')
    execute_time = cur_tick_ms() - tick
    protocol = util.PROTOCOL
    meta['profile'] = {
        'sd_bytes_len': 0,
        'runtime': {
            'fetch_data_time': 0,
            'sd_time': 0,
            'nt_time': 0,
        }
    }

    def splitter_es(meta, split_arr):
        es_time = 0
        sd_time = 0
        store_path = '/tmp/test_data_'
        out_dict = dict(meta)
        model_key = 'model'

        tick = cur_tick_ms()
        o = pickle.dumps(model)
        out_dict['profile']['sd_bytes_len'] += len(o)
        sd_time += cur_tick_ms() - tick

        tick = cur_tick_ms()
        out_dict['s3_obj_key_data'] = {
            'model': model_key
        }
        util.redis_put(model_key, o)
        es_time += cur_tick_ms() - tick

        for i, data in enumerate(split_arr):
            tick = cur_tick_ms()
            obj_key = 'digit_' + str(i)
            t = pickle.dumps(data)
            out_dict['profile']['sd_bytes_len'] += len(t)

            sd_time += cur_tick_ms() - tick

            tick = cur_tick_ms()
            util.redis_put(obj_key, t)
            out_dict['s3_obj_key_data'][str(i)] = obj_key
            es_time += cur_tick_ms() - tick

        out_dict['profile']['splitter'] = {
            'es_time': es_time,
            'sd_time': sd_time,
        }
        return out_dict

    def splitter_rrpc(meta, split_arr):
        out = splitter_es(meta, split_arr)
        out['profile']['splitter'].pop('es_time')
        return out

    def splitter_rpc(meta, split_arr):
        out_dict = meta
        out_dict['payload'] = {
            'model': model
        }
        tick = cur_tick_ms()
        for i, data in enumerate(split_arr):
            out_dict['payload'][str(i)] = data
        sd_time = cur_tick_ms() - tick
        out_dict['profile']['splitter'] = {
            'sd_time': sd_time
        }
        return out_dict

    def splitter_dmerge(meta, split_arr):
        global_obj['train_data'] = {}
        out_dict = dict(meta)
        out_dict['obj_hash'] = {}
        addr = int(os.environ.get('BASE_HEX', '100000000'), 16)
        datas = [t.tolist() for t in split_arr]
        push_start_time = cur_tick_ms()
        nic_idx = 0
        for i, data in enumerate(datas):
            global_obj[str(i)] = data
            out_dict['obj_hash'][str(i)] = id(global_obj[str(i)])

        gid, mac_id, hint = util.push(nic_id=nic_idx, peak_addr=addr)
        push_time = cur_tick_ms() - push_start_time
        out_dict['route'] = {
            'gid': gid,
            'machine_id': mac_id,
            'nic_id': nic_idx,
            'hint': hint
        }
        out_dict['profile'].update({
            'splitter': {
                'push_time': push_time,
            },
        })
        return out_dict

    predict_dispatcher = {
        'ES': splitter_es,
        'DMERGE': splitter_dmerge,
        'DMERGE_PUSH': splitter_dmerge,
        'RRPC': splitter_rrpc,
        'RPC': splitter_rpc,
    }
    dispatch_key = protocol
    out_dict = predict_dispatcher[dispatch_key](meta, split_arr)
    out_dict.update({
        'wf_id': str(uuid.uuid4()),
        'features': {'protocol': protocol},
    })
    out_dict['profile']['wf_start_tick'] = wf_start_tick
    out_dict['profile']['splitter']['execute_time'] = execute_time
    out_dict['profile']['splitter']['stage_time'] = sum(out_dict['profile']['splitter'].values())
    return out_dict


def predict(meta):
    start_tick = cur_tick_ms()

    def execute_body(model, data):
        # y_test = data[:, 0]
        x_test = data[:, 1:data.shape[1]]
        y_pred = model.predict(x_test)
        y_pred = [np.argmax(line) for line in y_pred]
        return y_pred

    def predict_es(_meta):
        current_app.logger.info(f"meta in predict s3: {_meta}")
        out_dict = dict(_meta)
        tick = cur_tick_ms()
        ID = os.environ.get('ID', 0)
        path = '/tmp/digits_' + str(ID) + '.txt'
        s3_obj = _meta['s3_obj_key_data'][str(ID)]
        bi = util.redis_get(s3_obj)
        model_o = util.redis_get(_meta['s3_obj_key_data']['model'])
        es_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        data = pickle.loads(bi)
        model = pickle.loads(model_o)
        sd_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        y_pred = execute_body(model, data)
        execute_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        pred_saved_path = "/tmp/pred.txt"
        t = pickle.dumps(y_pred)
        out_dict['profile']['sd_bytes_len'] += len(t)
        pred_obj_key = 'y_pred_' + str(ID)
        sd_time += cur_tick_ms() - tick

        tick = cur_tick_ms()
        util.redis_put(pred_obj_key, t)
        es_time += cur_tick_ms() - tick
        out_dict['s3_obj_key_pred'] = {
            'ID': str(ID),
            str(ID): pred_obj_key
        }
        out_dict['profile'].update({
            'predict': {
                'execute_time': execute_time,
                'es_time': es_time,
                'sd_time': sd_time,
            }
        })
        return out_dict

    def predict_rrpc(_meta):
        out = predict_es(_meta)
        out['profile']['predict'].pop('es_time')
        return out

    def predict_rpc(_meta):
        out_dict = _meta
        ID = os.environ.get('ID', 0)
        data = _meta['payload'][str(ID)]
        model = _meta['payload']['model']
        # tick = cur_tick_ms()
        # data = np.array(data_raw)
        # sd_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        y_pred = execute_body(model, data)
        execute_time = cur_tick_ms() - tick

        out_dict['payload'] = {
            'ID': str(ID),
            str(ID): y_pred
        }
        out_dict['profile'].update({
            'predict': {
                'execute_time': execute_time,
            }
        })
        return out_dict

    def predict_dmerge(_meta):
        out_dict = dict(_meta)

        tick = cur_tick_ms()
        ID = os.environ.get('ID', 0)
        route = _meta['route']
        gid, mac_id, hint, nic_id = route['gid'], route['machine_id'], \
            route['hint'], route['nic_id']
        r = util.pull(mac_id, hint)
        assert r == 0
        data = util.fetch(meta['obj_hash'][str(ID)])
        pull_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        test_data = np.array(data)
        pred_y = execute_body(test_data)
        execute_time = cur_tick_ms() - tick
        current_app.logger.debug(f"pred y finish. len {len(pred_y)}")
        push_start_time = cur_tick_ms()
        nic_idx = 0
        addr = int(os.environ.get('BASE_HEX', '100000000'), 16)
        global_obj[str(ID)] = pred_y
        out_dict['obj_hash'] = {}
        out_dict['obj_hash'][str(ID)] = id(global_obj[str(ID)])
        gid, mac_id, hint = util.push(nic_id=nic_idx, peak_addr=addr)
        push_time = cur_tick_ms() - push_start_time

        out_dict['route'] = {
            'gid': gid,
            'machine_id': mac_id,
            'nic_id': nic_idx,
            'hint': hint
        }
        current_app.logger.info(f"route@{ID}: {out_dict['route']}")
        out_dict['ID'] = str(ID)
        out_dict['profile'].update({
            'predict': {
                'execute_time': execute_time,
                'pull_time': pull_time,
                'push_time': push_time,
            }
        })
        return out_dict

    predict_dispatcher = {
        'ES': predict_es,
        'DMERGE': predict_dmerge,
        'DMERGE_PUSH': predict_dmerge,
        'RRPC': predict_rrpc,
        'RPC': predict_rpc,
    }
    dispatch_key = meta['features']['protocol']
    out_dict = predict_dispatcher[dispatch_key](meta)
    out_dict['profile']['predict']['stage_time'] = sum(out_dict['profile']['predict'].values())
    return out_dict


def combine(metas):
    start_tick = cur_tick_ms()

    def combine_es(event):
        tick = cur_tick_ms()
        ID = event['s3_obj_key_pred']['ID']
        path = '/tmp/digits_' + str(ID) + '.txt'
        s3_obj = event['s3_obj_key_pred'][str(ID)]
        bi = util.redis_get(s3_obj)
        es_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        pred_data = pickle.loads(bi)
        sd_time = cur_tick_ms() - tick

        out_dict = event
        out_dict['pred'] = pred_data
        out_dict['profile']['combine'] = {
            'es_time': es_time,
            'sd_time': sd_time,
        }
        return out_dict

    def combine_rrpc(event):
        out = combine_es(event)
        out['profile']['combine'].pop('es_time')
        return out

    def combine_rpc(event):
        ID = event['payload']['ID']
        pred_data = event['payload'][str(ID)]

        out_dict = dict(event)
        out_dict['payload'] = pred_data
        out_dict['profile']['combine'] = {
        }
        return out_dict

    def combine_dmerge(event):
        out_dict = dict(event)

        tick = cur_tick_ms()
        ID = event['ID']
        route = event['route']
        gid, mac_id, hint, nic_id = route['gid'], route['machine_id'], \
            route['hint'], route['nic_id']
        current_app.logger.debug(f"Ready to pull: mac id: {mac_id} ,"
                                 f"hint: {hint} ,"
                                 f"ID: {ID}")
        r = util.pull(mac_id, hint)
        assert r == 0
        data = util.fetch(event['obj_hash'][str(ID)])
        pull_time = cur_tick_ms() - tick

        out_dict['pred'] = data  # TODO: merge result
        out_dict['profile']['combine'] = {
            'pull_time': pull_time,
        }
        return out_dict

    combine_dispatcher = {
        'ES': combine_es,
        'DMERGE': combine_dmerge,
        'DMERGE_PUSH': combine_dmerge,
        'RRPC': combine_rrpc,
        'RPC': combine_rpc,
    }
    wf_e2e_time = 0
    T = cur_tick_ms()
    for i, event in enumerate(metas):
        dispatch_key = event['features']['protocol']
        out_dict = combine_dispatcher[dispatch_key](event)
        out_dict['profile']['runtime']['stage_time'] = sum(out_dict['profile']['runtime'].values())
        out_dict['profile']['combine']['stage_time'] = sum(out_dict['profile']['combine'].values())
        wf_e2e_time = max(wf_e2e_time, T - event['profile']['wf_start_tick'])
        current_app.logger.info(f"event@{i} profile: {out_dict['profile']}")
    # Compute mean of the times:
    # current_app.logger.info(f"[ {util.PROTOCOL} ] workflow tick offset: {wf_e2e_time}")

    profile_len = len(metas)
    profile = metas[0]['profile']
    rm_keys = set()
    for event in metas[1:]:
        for stage, detail in event['profile'].items():
            if isinstance(detail, dict):
                for category, time_span in detail.items():
                    profile[stage][category] += time_span
            else:
                rm_keys.add(stage)
    for s in rm_keys:
        profile.pop(s)
    for stage, detail in profile.items():
        if isinstance(detail, dict):
            for category, time_span in detail.items():
                profile[stage][category] /= profile_len
    reduced_profile = util.reduce_profile(profile)
    current_app.logger.info(f"[ {util.PROTOCOL} ] workflow e2e time: {reduced_profile['stage_time']}")
    for k, v in reduced_profile.items():
        current_app.logger.info(f"Part@ {k} passed {v} ms")
    return {}


def default_handler(meta):
    current_app.logger.info(f'not a default path for type')
    return meta


if __name__ == '__main__':
    res = predict({})
