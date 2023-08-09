import pyarrow as pa
import pandas as pd
import pyarrow.flight as fl


class FlightServer(fl.FlightServerBase):
    def __init__(self, host, port):
        location = fl.Location.for_grpc_tcp(host, port)
        super().__init__(location)
        self.table = pa.Table.from_pandas(pd.read_csv('../data/yfinance.csv'))

    def list_flights(self, context, criteria):
        return [fl.FlightInfo("example", [self.table.schema])]

    def do_get(self, context, ticket):
        return pa.flight.RecordBatchStream(self.table)

    def get_flight_info(self, context, descriptor):
        if descriptor == "example":
            return pa.flight.FlightInfo("example", [self.table.schema])


if __name__ == "__main__":
    host = "localhost"
    port = 5005
    server = FlightServer(host, port)
    server.serve()
