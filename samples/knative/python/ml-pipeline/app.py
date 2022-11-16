import os

import redis
from flask import Flask, request, make_response
import uuid
import requests
import redis_client
import util
from cloudevents.http import from_http, CloudEvent
from functions import *

app = Flask(__name__)

# Env list
ce_specversion = os.environ.get('CE_SPECVERSION', '0.3')
ce_type = os.environ.get("CE_TYPE", "default")

PING_TP = 'dev.knative.sources.ping'
SPLITTER_TP = 'splitter'
TRAINER_TP = 'trainer'


# Thanks the CE python SDK https://github.com/cloudevents/sdk-python
@app.route('/', methods=['POST'])
def faas_entry():
    event = from_http(request.headers, request.get_data())
    data = handle_ce(event)
    response = make_response(data)
    response.headers = util.fill_ce_header(id=str(uuid.uuid4()),
                                           ce_specversion=ce_specversion,
                                           ce_type=ce_type,
                                           ce_source="ml-pipeline")
    return response


def handle_ce(event: CloudEvent):
    meta = event.data
    source_tp = event['type']
    if source_tp == PING_TP:
        out_data = splitter(meta)
    elif source_tp == SPLITTER_TP:
        out_data = trainer(meta)
    elif source_tp == TRAINER_TP:
        out_data = reduce(meta)  # Finish
    else:  # Default case
        out_data = reduce(meta)
    return out_data


if __name__ == '__main__':
    port = 8080
    app.run(debug=True, host='0.0.0.0', port=port)
