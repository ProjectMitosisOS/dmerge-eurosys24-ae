import os
import pickle
import threading
import uuid

import numpy as np
import pandas as pd
import requests
from bindings import *
import logging

app_logger = logging.getLogger('app_logger')
import util
from util import cur_tick_ms

global_obj = {}


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


def source(_meta):
    protocol = util.PROTOCOL
    loop = int(_meta.get('loop', '0'))
    out_dict = {}

    wf_start_tick = cur_tick_ms()

    out_dict.update({
        'wf_id': str(uuid.uuid4()),
        'features': {'protocol': protocol},
        'profile': {
            'loop': loop,
            'sd_bytes_len': 0,
            'leave_tick': cur_tick_ms(),
            'wf_start_tick': wf_start_tick,
            'runtime': {
                'fetch_data_time': 0,
                'sd_time': 0,
                'nt_time': 0,
            }
        },
        "body": {"portfolioType": "S&P", "portfolio": "1234"}
    })

    return out_dict


local_file_path = 'yfinance.csv'
whole_set_origin = pd.read_csv(local_file_path)

def fetchData(meta):
    start_tick = cur_tick_ms()
    app_logger.debug(f"in fetchData, meta: {meta}")
    stage_name = 'fetchData'

    def fetch_market_data(meta):
        """
        Fetch public data
        :param meta:
        :return:
        """
        TOUCH_RATIO = int(os.environ.get('TOUCH_RATIO', '2')) / 100
        # download
        tick = cur_tick_ms()

        protocol = meta['features']['protocol']

        portfolioType = meta['body']['portfolioType']
        tickers_for_portfolio_types = {'S&P': ['GOOG', 'AMZN', 'MSFT', 'SVFAU', 'AB', 'ABC', 'ABCB']}
        tickers = tickers_for_portfolio_types[portfolioType]

        prices = {}

        for ticker in tickers:
            # Get last closing price
            prices[ticker] = whole_set_origin['Close'][0]
        pd_time = cur_tick_ms() - tick
        tick = cur_tick_ms()
        out_meta = dict(meta)
        execute_time = cur_tick_ms() - tick
        local_file_name = 'whole_data.csv'

        # Dump data
        out_meta['profile'][stage_name] = {
            'execute_time': execute_time,
            'pd_time': pd_time,
        }

        def public_data_es(meta, whole_set):
            tick = cur_tick_ms()
            first_n = int(len(whole_set) * TOUCH_RATIO)
            o = pickle.dumps(whole_set.head(first_n))
            # with open(local_file_name, 'wb') as f:
            #     pickle.dump(whole_set.head(first_n), f)
            # whole_set.head(first_n).to_csv(local_file_name)
            out_meta['profile']['sd_bytes_len'] += len(o)
            sd_time = cur_tick_ms() - tick

            tick = cur_tick_ms()
            s3_obj_key = 'whole_data'
            util.redis_put(s3_obj_key, o)
            es_time = cur_tick_ms() - tick

            meta['profile'][stage_name]['sd_time'] = sd_time
            meta['profile'][stage_name]['es_time'] = es_time
            meta['s3_obj_key'] = s3_obj_key

        def public_data_rrpc(meta, whole_set):
            public_data_es(meta, whole_set)

        def public_data_rpc(meta, whole_set):
            tick = cur_tick_ms()
            first_n = int(len(whole_set) * TOUCH_RATIO)
            app_logger.info(f'first n: {first_n}')
            data = whole_set.head(first_n)
            sd_time = cur_tick_ms() - tick

            meta['payload'] = data
            meta['profile'][stage_name]['sd_time'] = sd_time

        def public_data_dmerge(meta, data):
            tick = cur_tick_ms()
            np_arr = np.array(data)
            data_li = np_arr[:int(len(np_arr) * TOUCH_RATIO)].tolist()
            exec_time = cur_tick_ms() - tick

            tick = cur_tick_ms()
            global_obj['wholeset_matrix'] = data_li
            meta['obj_hash'] = {
                'wholeset_matrix': id(global_obj['wholeset_matrix'])
            }
            nic_idx = 0
            addr = int(os.environ.get('BASE_HEX', '100000000'), 16)
            gid, mac_id, hint = util.push(nic_id=nic_idx, peak_addr=addr)
            push_time = cur_tick_ms() - tick

            meta['route'] = {
                'gid': gid,
                'machine_id': mac_id,
                'nic_id': nic_idx,
                'hint': hint
            }
            meta['profile'][stage_name]['push_time'] = push_time
            app_logger.debug(f'finish merging at heap id {hint}')
            # meta['profile'][stage_name]['execute_time'] += exec_time

        public_data_dispatcher = {
            'ES': public_data_es,
            'RPC': public_data_rpc,
            'DMERGE': public_data_dmerge,
            'DMERGE_PUSH': public_data_dmerge,
            'RRPC': public_data_rrpc
        }
        public_data_dispatcher[protocol](out_meta, whole_set_origin)
        out_meta.update({
            'statusCode': 200,
            'body': {'marketData': prices},
            'data_type': 'market_data'
        })

        return out_meta

    def fetch_portfolio_data(meta):
        portfolio = meta['body']['portfolio']
        tick = cur_tick_ms()
        data = util.portfolios[portfolio]

        valid = True

        for trade in data:
            side = trade['Side']
            # Tag ID: 552, Tag Name: Side, Valid values: 1,2,8
            if not (side == 1 or side == 2 or side == 8):
                valid = False
                break
        execute_time = cur_tick_ms() - tick
        out_meta = dict(meta)
        out_meta.update({
            'statusCode': 200,
            'body': {'valid': valid, 'portfolio': portfolio},
            'data_type': 'portfolio_data'
        })
        out_meta['profile'][stage_name] = {
            'execute_time': execute_time,
        }
        return out_meta

    ID = int(os.environ.get('ID', '0'))
    fetch_datas = [fetch_market_data, fetch_portfolio_data]
    out_dict = fetch_datas[ID](meta)
    out_dict['profile']['leave_tick'] = cur_tick_ms()
    out_dict['profile'][stage_name]['stage_time'] = sum(out_dict['profile'][stage_name].values())
    app_logger.debug(f"FetchData out profile: {out_dict['profile']}")
    return out_dict


# lock = threading.Lock()


def runAuditRule(events):
    # lock.acquire()
    stage_name = 'runAuditRule'

    def checkMarginBalance(portfolioData, marketData, portfolio):
        marginAccountBalance = {
            "1234": 4500
        }[portfolio]

        portfolioMarketValue = 0
        for trade in portfolioData:
            security = trade['Security']
            qty = trade['LastQty']
            portfolioMarketValue += qty * marketData[security]

        # Maintenance Margin should be atleast 25% of market value for "long" securities
        # https://www.finra.org/rules-guidance/rulebooks/finra-rules/4210#the-rule
        result = False
        if marginAccountBalance >= 0.25 * portfolioMarketValue:
            result = True

        return result

    market_data = {}
    valid_format = True
    finance_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Dividends',
                       'Stock Splits']
    for event in events:
        body = event['body']
        if 'marketData' in body:
            protocol = event['features']['protocol']
            market_data = body['marketData']

            # Get whole set
            def handle_public_dmerge(event):

                tick = cur_tick_ms()
                route = event['route']
                gid, mac_id, hint, nic_id = route['gid'], route['machine_id'], \
                    route['hint'], route['nic_id']
                # TODO: Support concurrency of pulling
                for i in range(1 if protocol == 'DMERGE' else 2):
                    r = util.pull(mac_id, hint)
                    assert r == 0

                data = util.fetch(event['obj_hash']['wholeset_matrix'])
                pull_time = cur_tick_ms() - tick

                # data_np = np.array(data)
                # whole_set = pd.DataFrame(data_np, columns=finance_columns)

                tick = cur_tick_ms()
                execute_time = cur_tick_ms() - tick
                event['profile'].update({
                    stage_name: {
                        'pull_time': pull_time,
                        'execute_time': execute_time,
                    }
                })
                return None  # FIXME: Shall not return wholeset

            def handle_public_es(event):
                tick = cur_tick_ms()
                s3_obj_key = event['s3_obj_key']
                o = util.redis_get(s3_obj_key)
                es_time = cur_tick_ms() - tick

                tick = cur_tick_ms()
                whole_set = pickle.loads(o)
                # whole_set = pd.read_csv(local_path)
                sd_time = cur_tick_ms() - tick

                event['profile'].update({
                    stage_name: {
                        'es_time': es_time,
                        'sd_time': sd_time,
                        'execute_time': 0,
                    }
                })
                return whole_set

            def handle_public_rpc(event):
                tick = cur_tick_ms()
                whole_set = event['payload']
                sd_time = cur_tick_ms() - tick

                event['profile'].update({
                    stage_name: {
                        'sd_time': sd_time,
                        'execute_time': 0,
                    }
                })
                return whole_set

            dispatcher = {
                'ES': handle_public_es,
                'RPC': handle_public_rpc,
                'DMERGE': handle_public_dmerge,
                'DMERGE_PUSH': handle_public_dmerge,
                'RRPC': handle_public_rpc,
            }
            dispatcher[protocol](event)

        elif 'valid' in body:
            portfolio = event['body']['portfolio']
            valid_format = valid_format and body['valid']
            event['profile'].update({stage_name: {'execute_time': 0}})

    tick = cur_tick_ms()
    portfolioData = util.portfolios[portfolio]
    marginSatisfied = checkMarginBalance(portfolioData, market_data, portfolio)
    execute_time = cur_tick_ms() - tick
    for event in events:
        event['profile']['runtime']['stage_time'] = sum(event['profile']['runtime'].values())
        event['profile'][stage_name]['execute_time'] += execute_time
        event['profile'][stage_name]['stage_time'] = sum(event['profile'][stage_name].values())
        event['profile']['wf_end_tick'] = cur_tick_ms()

    out_meta = events[-1]
    # lock.release()
    return out_meta


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
    app_logger.info(f'not a default path for type')
    return meta
