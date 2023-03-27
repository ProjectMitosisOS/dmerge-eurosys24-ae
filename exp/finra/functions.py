import os
import uuid

import numpy as np
import pandas as pd
from bindings import *
from flask import current_app
from minio import Minio

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

touch_ratio = 0.02


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

    out_dict = {}
    s3_obj_key = 'yfinance.csv'
    s3_client.fput_object(bucket_name, s3_obj_key, 'yfinance.csv')

    wf_start_tick = cur_tick_ms()

    out_dict.update({
        'wf_id': str(uuid.uuid4()),
        's3_obj_key': s3_obj_key,
        'features': {'protocol': protocol},
        'profile': {
            'leave_tick': cur_tick_ms(),
            'wf_start_tick': wf_start_tick
        },
        "body": {"portfolioType": "S&P", "portfolio": "1234"}
    })

    return out_dict


def fetchData(meta):
    start_tick = cur_tick_ms()
    current_app.logger.info(f"in fetchData, meta: {meta}")
    nt_time = start_tick - meta['profile']['leave_tick']
    stage_name = 'fetchData'

    def fetch_market_data(meta):
        """
        Fetch public data
        :param meta:
        :return:
        """
        # download
        tick = cur_tick_ms()
        local_file_path = '/tmp/yfinance.csv'
        protocol = meta['features']['protocol']
        s3_obj_key = meta['s3_obj_key']
        s3_client.fget_object(bucket_name, s3_obj_key, local_file_path)

        portfolioType = meta['body']['portfolioType']
        tickers_for_portfolio_types = {'S&P': ['GOOG', 'AMZN', 'MSFT', 'SVFAU', 'AB', 'ABC', 'ABCB']}
        tickers = tickers_for_portfolio_types[portfolioType]

        prices = {}
        whole_set = pd.read_csv(local_file_path)
        for ticker in tickers:
            # Get last closing price
            prices[ticker] = whole_set['Close'].unique()[0]

        out_meta = dict(meta)

        local_file_name = 'whole_data.csv'
        execute_time = cur_tick_ms() - tick

        # Dump data
        out_meta['profile'][stage_name] = {
            'execute_time': execute_time,
            'nt_time': nt_time
        }

        def public_data_s3(meta, whole_set):
            tick = cur_tick_ms()
            first_n = int(len(whole_set) * touch_ratio)
            whole_set.head(first_n).to_csv(local_file_name)
            sd_time = cur_tick_ms() - tick

            tick = cur_tick_ms()
            s3_obj_key = 'whole_data'
            s3_client.fput_object(bucket_name, s3_obj_key, local_file_name)
            s3_time = cur_tick_ms() - tick

            meta['profile'][stage_name]['sd_time'] = sd_time
            meta['profile'][stage_name]['s3_time'] = s3_time
            meta['s3_obj_key'] = s3_obj_key

        def public_data_dmerge(meta, data):
            tick = cur_tick_ms()
            np_arr = np.array(data)
            data_li = np_arr[:int(len(np_arr) * touch_ratio)].tolist()
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
            meta['profile'][stage_name]['execute_time'] += exec_time

        public_data_dispatcher = {
            'S3': public_data_s3,
            'DMERGE': public_data_dmerge,
            'DMERGE_PUSH': public_data_dmerge,
            'P2P': public_data_s3
        }
        public_data_dispatcher[protocol](out_meta, whole_set)
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
            'nt_time': nt_time
        }
        return out_meta

    ID = int(os.environ.get('ID', '0'))
    fetch_datas = [fetch_market_data, fetch_portfolio_data]
    out_dict = fetch_datas[ID](meta)
    out_dict['profile']['leave_tick'] = cur_tick_ms()
    out_dict['profile'][stage_name]['stage_time'] = sum(out_dict['profile'][stage_name].values())
    current_app.logger.info(f"FetchData out profile: {out_dict['profile']}")
    return out_dict


def runAuditRule(events):
    start_tick = cur_tick_ms()
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
    whole_set = {}
    valid_format = True
    execute_time = 0
    finance_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Dividends',
                       'Stock Splits']
    for event in events:
        body = event['body']
        if 'marketData' in body:
            protocol = event['features']['protocol']
            tick = cur_tick_ms()
            market_data = body['marketData']
            # Get whole set
            if protocol in ['DMERGE', 'DMERGE_PUSH']:
                tick = cur_tick_ms()
                route = event['route']
                gid, mac_id, hint, nic_id = route['gid'], route['machine_id'], \
                    route['hint'], route['nic_id']
                r = util.pull(mac_id, hint)
                assert r == 0
                data = util.fetch(event['obj_hash']['wholeset_matrix'])
                pull_time = cur_tick_ms() - tick

                tick = cur_tick_ms()
                data_np = np.array(data)
                whole_set = pd.DataFrame(data_np, columns=finance_columns)
                execute_time += cur_tick_ms() - tick
                event['profile'].update({
                    stage_name: {
                        'pull_time': pull_time,
                        'nt_time': start_tick - event['profile']['leave_tick']
                    }
                })
            else:
                s3_obj_key = event['s3_obj_key']
                local_path = 'tmp.csv'
                s3_client.fget_object(bucket_name, s3_obj_key, local_path)
                s3_time = cur_tick_ms() - tick

                tick = cur_tick_ms()
                whole_set = pd.read_csv(local_path)
                sd_time = cur_tick_ms() - tick

                event['profile'].update({
                    stage_name: {
                        's3_time': s3_time,
                        'sd_time': sd_time,
                        'nt_time': start_tick - event['profile']['leave_tick']
                    }
                })
        elif 'valid' in body:
            portfolio = event['body']['portfolio']
            valid_format = valid_format and body['valid']
            event['profile'].update({stage_name: {}})

    tick = cur_tick_ms()
    portfolioData = util.portfolios[portfolio]
    marginSatisfied = checkMarginBalance(portfolioData, market_data, portfolio)
    avg_data = [whole_set[key] for key in finance_columns]
    sum_data = [whole_set[key] for key in finance_columns]
    std_data = [whole_set[key] for key in finance_columns]
    whole_data = [avg_data[0], sum_data[0], std_data[0]]
    execute_time += cur_tick_ms() - tick
    for event in events:
        event['profile'][stage_name]['execute_time'] = execute_time
        event['profile'][stage_name]['stage_time'] = sum(event['profile'][stage_name].values())
    out_meta = {
        'events': [event['profile'] for event in events],
    }

    current_app.logger.info(f"return meta {out_meta}")
    current_app.logger.info(f"workflow e2e time {cur_tick_ms() - events[-1]['profile']['wf_start_tick']}")
    return out_meta


def default_handler(meta):
    current_app.logger.info(f'not a default path for type')
    return meta
