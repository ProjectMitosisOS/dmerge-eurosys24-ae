import numpy as np
import pandas as pd
from minio import Minio
import time

portfolios = {
    "1234": [
        {
            "Security": "GOOG",
            "LastQty": 10,
            "LastPx": 1363.85123,
            "Side": 1,
            "TrdSubType": 0,
            "TradeDate": "200507"
        },
        {
            "Security": "MSFT",
            "LastQty": 20,
            "LastPx": 183.851234,
            "Side": 1,
            "TrdSubType": 0,
            "TradeDate": "200507"
        }
    ]
}

s3_client = Minio(
    endpoint='127.0.0.1:9000',
    secure=False,
    access_key='wSgN80XAPlP5tLgD', secret_key='z9YsQtR2QENolHcM4mrqWLPSYiJBoa7W')
bucketName = 'finra'
if not s3_client.bucket_exists(bucketName):
    s3_client.make_bucket(bucketName)


def cur_tick_ms():
    return int(round(time.time() * 1000))


# parallel step1: public data
def public_data(event):
    """
    Fetch public market data from yahoo finance api
    :return:
    """
    externalServicesTime = 0
    portfolioType = event['body']['portfolioType']

    tickers_for_portfolio_types = {'S&P': ['GOOG', 'AMZN', 'MSFT', 'SVFAU', 'AB', 'ABC', 'ABCB']}
    tickers = tickers_for_portfolio_types[portfolioType]

    prices = {}
    tick = cur_tick_ms()
    whole_set = pd.read_csv("yfinance.csv")

    for ticker in tickers:
        # Get last closing price
        tickTime = 1000 * time.time()
        externalServicesTime += 1000 * time.time() - tickTime
        prices[ticker] = whole_set['Close'].unique()[0]

    out_meta = {'statusCode': 200,
                'body': {'marketData': prices}}
    s3_obj_key = 'whole_data'
    local_file_name = 'whole_data.npy'
    d = np.array(whole_set)
    execute_time = cur_tick_ms() - tick

    tick = cur_tick_ms()
    np.save(local_file_name, d)
    sd_time = cur_tick_ms() - tick

    tick = cur_tick_ms()
    s3_client.fput_object(bucketName, s3_obj_key, local_file_name)
    s3_time = cur_tick_ms() - tick

    out_meta['s3_obj_key'] = s3_obj_key
    out_meta['profile'] = {
        'public_data': {
            'execute_time': execute_time,
            'sd_time': sd_time,
            's3_time': s3_time
        }
    }

    return out_meta


# parallel step2: private data
def private_data(event):
    portfolio = event['body']['portfolio']
    tick = cur_tick_ms()
    data = portfolios[portfolio]

    valid = True

    for trade in data:
        side = trade['Side']
        # Tag ID: 552, Tag Name: Side, Valid values: 1,2,8
        if not (side == 1 or side == 2 or side == 8):
            valid = False
            break
    execute_time = cur_tick_ms() - tick
    out_meta = {
        'statusCode': 200,
        'body': {'valid': valid, 'portfolio': portfolio},
        'profile': {
            'private_data': {
                'execute_time': execute_time
            }
        }}
    return out_meta


# parallel steps: bargain balance


def bargin_balance(events):
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

    marketData = {}
    whole_set = {}
    validFormat = True
    finance_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Dividends',
                       'Stock Splits']
    execute_time = 0
    s3_time = 0
    sd_time = 0

    for event in events:
        body = event['body']
        if 'marketData' in body:
            tick = cur_tick_ms()
            marketData = body['marketData']
            # Get whole set
            s3_obj_key = event['s3_obj_key']
            local_path = 'tmp.npy'
            s3_client.fget_object(bucketName, s3_obj_key, local_path)
            s3_time += cur_tick_ms() - tick

            tick = cur_tick_ms()
            data = np.load(local_path, allow_pickle=True)
            whole_set = pd.DataFrame(data, columns=finance_columns)
            sd_time += cur_tick_ms() - tick
        elif 'valid' in body:
            portfolio = event['body']['portfolio']
            validFormat = validFormat and body['valid']

    tick = cur_tick_ms()
    portfolioData = portfolios[portfolio]
    marginSatisfied = checkMarginBalance(portfolioData, marketData, portfolio)
    avg_data = np.array([np.average(whole_set[key].tolist()) for key in finance_columns[1:]])
    sum_data = np.array([np.sum(whole_set[key].tolist()) for key in finance_columns[1:]])
    std_data = np.array([np.std(whole_set[key].tolist()) for key in finance_columns[1:]])
    X = np.array([whole_set[key].tolist() for key in finance_columns[1:]])
    cov_matrix = np.cov(X, rowvar=False)

    whole_data = [avg_data, sum_data, std_data]
    execute_time = cur_tick_ms() - tick
    out_meta = {
        'statusCode': 200,
        'body': {
            'validFormat': validFormat,
            'marginSatisfied': marginSatisfied,
            'whole_data': whole_data
        },
        'profile': {
            'bargain_balance': {
                'execute_time': execute_time,
                's3_time': s3_time,
                'sd_time': sd_time
            }
        }}
    return out_meta


if __name__ == '__main__':
    tick = cur_tick_ms()
    req = {"body": {"portfolioType": "S&P", "portfolio": "1234"}}
    events = [public_data(req), private_data(req)]
    res = bargin_balance(events)
    print(f'time passed {cur_tick_ms() - tick} ms')
    print(events[0]['profile'])
    print(events[1]['profile'])
    print(res['profile'])
