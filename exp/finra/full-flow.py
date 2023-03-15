import socket
import time

import numpy as np
import pandas as pd
from util import *
import os


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
    whole_set = pd.read_csv("yfinance.csv")
    for ticker in tickers:
        # Get last closing price
        tickTime = 1000 * time.time()
        data = pd.read_csv("yfinance.csv")
        externalServicesTime += 1000 * time.time() - tickTime
        prices[ticker] = whole_set['Close'].unique()[0]

    response = {'statusCode': 200,
                'body': {'marketData': prices, 'whole_set': whole_set}}

    return response


# parallel step2: private data
def private_data(event):
    portfolio = event['body']['portfolio']

    data = portfolios[portfolio]

    valid = True

    for trade in data:
        side = trade['Side']
        # Tag ID: 552, Tag Name: Side, Valid values: 1,2,8
        if not (side == 1 or side == 2 or side == 8):
            valid = False
            break
    response = {'statusCode': 200, 'body': {'valid': valid, 'portfolio': portfolio}}
    return response


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

    for event in events:
        body = event['body']
        if 'marketData' in body:
            marketData = body['marketData']
            whole_set = body['whole_set']
        elif 'valid' in body:
            portfolio = event['body']['portfolio']
            validFormat = validFormat and body['valid']

    portfolioData = portfolios[portfolio]
    marginSatisfied = checkMarginBalance(portfolioData, marketData, portfolio)
    finance_columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Dividends', 'Stock Splits']
    avg_data = [np.average(whole_set[key]) for key in finance_columns]
    sum_data = [np.sum(whole_set[key]) for key in finance_columns]
    std_data = [np.std(whole_set[key]) for key in finance_columns]
    whole_data = [avg_data, sum_data, std_data]
    response = {'statusCode': 200,
                'body': {'validFormat': validFormat,
                         'marginSatisfied': marginSatisfied,
                         'whole_data': whole_data
                         }}
    return response


if __name__ == '__main__':
    tick = cur_tick_ms()
    req = {"body": {"portfolioType": "S&P", "portfolio": "1234"}}
    events = [public_data(req), private_data(req)]
    res = bargin_balance(events)
    print(f'time passed {cur_tick_ms() - tick} ms')
    print(res)
