import pandas as pd
import yfinance as yf

# ticker symbol lookup in https://finance.yahoo.com/lookup
tickers = ['GOOG', 'AMZN', 'MSFT', 'SVFAU', 'AB',
           # 'ABC', 'ABCB', 'AAPL', 'NFLX', 'CS',
           # 'CAMZX', 'AMUB', 'MLPR', 'AMZA', 'AMJ',
           # 'PCAR', 'PEP', 'BAC', 'NVDA', 'TSLA',
           # 'META', 'TSM', 'UNH', 'XOM', 'JNJ',
           # 'WMT', 'JPM', 'PG', 'MA', 'NVO',
           # 'LLY', 'HD', 'MRK', 'ABBV', 'KO', 'AVGO'
           ]
dfs = []

for ticker in tickers:
    tickerObj = yf.Ticker(ticker)
    # Get historical data
    data = tickerObj.history(period="max")
    dfs.append(data)

result = pd.concat(dfs)
result.to_csv("yfinance.csv", index=True)
