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
        tick = cur_tick_ms()
        local_file_path = '/tmp/yfinance.csv'
        s3_obj_key = meta['s3_obj_key']
        s3_client.fget_object(bucket_name, s3_obj_key, local_file_path)
        s3_time = cur_tick_ms() - tick

        portfolioType = meta['body']['portfolioType']
        tickers_for_portfolio_types = {'S&P': ['GOOG', 'AMZN', 'MSFT', 'SVFAU', 'AB', 'ABC', 'ABCB']}
        tickers = tickers_for_portfolio_types[portfolioType]

        prices = {}
        tick = cur_tick_ms()
        whole_set = pd.read_csv(local_file_path)
        sd_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        for ticker in tickers:
            # Get last closing price
            prices[ticker] = whole_set['Close'].unique()[0]

        out_meta = dict(meta)

        s3_obj_key = 'whole_data'
        local_file_name = 'whole_data.npy'
        wholeset_matrix = np.array(whole_set)
        execute_time = cur_tick_ms() - tick

        tick = cur_tick_ms()
        np.save(local_file_name, wholeset_matrix)
        sd_time += cur_tick_ms() - tick

        tick = cur_tick_ms()
        s3_client.fput_object(bucket_name, s3_obj_key, local_file_name)
        s3_time += cur_tick_ms() - tick
        out_meta.update({
            'statusCode': 200,
            'body': {'marketData': prices},
            's3_obj_key': s3_obj_key,
            'data_type': 'market_data'
        })
        out_meta['profile'][stage_name] = {
            'execute_time': execute_time,
            'sd_time': sd_time,
            's3_time': s3_time,
            'nt_time': nt_time
        }

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
    finance_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Dividends',
                       'Stock Splits']
    s3_time = 0
    sd_time = 0

    for event in events:
        body = event['body']
        if 'marketData' in body:
            tick = cur_tick_ms()
            market_data = body['marketData']
            # Get whole set
            s3_obj_key = event['s3_obj_key']
            local_path = 'tmp.npy'
            s3_client.fget_object(bucket_name, s3_obj_key, local_path)
            s3_time += cur_tick_ms() - tick

            tick = cur_tick_ms()
            data = np.load(local_path, allow_pickle=True)
            whole_set = pd.DataFrame(data, columns=finance_columns)
            sd_time += cur_tick_ms() - tick
        elif 'valid' in body:
            portfolio = event['body']['portfolio']
            valid_format = valid_format and body['valid']

    tick = cur_tick_ms()
    portfolioData = util.portfolios[portfolio]
    marginSatisfied = checkMarginBalance(portfolioData, market_data, portfolio)
    avg_data = [whole_set[key] for key in finance_columns]
    sum_data = [whole_set[key] for key in finance_columns]
    std_data = [whole_set[key] for key in finance_columns]
    whole_data = [avg_data[0], sum_data[0], std_data[0]]
    execute_time = cur_tick_ms() - tick
    for event in events:
        event['profile'].update({
            stage_name: {
                'execute_time': execute_time,
                's3_time': s3_time,
                'sd_time': sd_time,
                'nt_time': start_tick - event['profile']['leave_tick']
            }
        })
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
