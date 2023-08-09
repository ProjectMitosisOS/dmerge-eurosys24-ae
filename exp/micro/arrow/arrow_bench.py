import pandas as pd
import pyarrow.flight
import pyarrow as pa
import time
import pyarrow.flight as fl


def cur_tick_us():
    return int(round(time.time() * 1000000))


client = pyarrow.flight.FlightClient("grpc://localhost:5005")

ticket = fl.Ticket("example")
table = client.do_get(ticket).read_all()

tick = cur_tick_us()
df = table.to_pandas()
print(f'time is : {cur_tick_us() - tick}')






