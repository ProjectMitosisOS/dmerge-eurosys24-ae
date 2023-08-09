import pyarrow as pa
import pandas as pd
import time

# Define the nested dictionary
data = {
    'name': 'John',
    'age': 30,
    'city': 'New York',
    'detail': {
        'public': {
            'name': 'sample'
        }
    }
}


def cur_tick_us():
    return int(round(time.time() * 1000000))


df = pd.DataFrame(data)
print(df)
table = pa.Table.from_pandas(df)
print(table)

tick = cur_tick_us()
pa.serialize(table)

print(f'time: {(cur_tick_us() - tick) / 1000} ms')
