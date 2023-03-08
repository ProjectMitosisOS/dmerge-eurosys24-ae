import os
import uuid

from cloudevents.http import from_http, CloudEvent
from flask import Flask, request, make_response
import logging

import util
from functions import *

app = Flask(__name__)
app.logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Env list
ce_specversion = os.environ.get('CE_SPECVERSION', '0.3')
ce_type = os.environ.get("CE_TYPE", "default")

PING_TP = 'dev.knative.sources.ping'
SPLITTER_TP = 'splitter'
PRODUCER_TP = 'producer'
CONSUMER_TP = 'consumer'


# Thanks the CE python SDK https://github.com/cloudevents/sdk-python
@app.route('/', methods=['POST'])
def faas_entry():
    event = from_http(request.headers, request.get_data())
    data = handle_ce(event)
    response = make_response(data)
    response.headers = util.fill_ce_header(id=str(uuid.uuid4()),
                                           ce_specversion=ce_specversion,
                                           ce_type=ce_type,
                                           ce_source="p2p")
    return response


"""
upstream_info is a local-level cache that caching up upstream flows.
Its target is to waiting all upstream-parallel workers to finish.
By setting the env variable `UPSTREAM_NUM` to your parallel worker number.

If do not need to wait, we omit the env variable `UPSTREAM_NUM`.
{
    "stage_name1": {
        wf_id: [event1, event2]
    },
    "stage_name2": {
        wf_id1: [event1],
        wf_id2: [event2, event3]
    },
}
"""
upstream_info = {}
upstream_num_env_str = 'UPSTREAM_NUM'

stage_list = ['consumer']


def init():
    for stage in stage_list:
        upstream_info[stage] = {}


def handle_reduce(meta, stage_name):
    from flask import current_app
    stage = stage_name
    wf_id = meta["wf_id"]

    stream_cnt = int(os.environ.get(upstream_num_env_str, "1"))
    """
    cur_stage_info as below:
    {
        wf_id: [event1, event2]
    },
    """
    cur_stage_info = dict(upstream_info[stage])
    if wf_id not in cur_stage_info.keys():
        cur_stage_info[wf_id] = [meta]
    else:
        cur_stage_info[wf_id].append(meta)
    # write back
    upstream_info[stage][wf_id] = cur_stage_info[wf_id]

    if len(cur_stage_info[wf_id]) >= stream_cnt:  # TODO: Shall we guarantee the contention ?
        # Finish reduce
        current_app.logger.debug(f'Finish reduce at stage {stage}. upstream_info {upstream_info}')
        upstream_info[stage].pop(wf_id)
        return cur_stage_info[wf_id]
    else:
        current_app.logger.debug(
            f'Wait for next at stage {stage}. upstream_info {upstream_info}, Upstream cnt {stream_cnt}')
        return None


def handle_ce(event: CloudEvent):
    meta = event.data
    source_tp = event['type']
    if source_tp == PING_TP:
        out_data = splitter(meta)
        # First step: setup wf_id
        out_data['wf_id'] = str(uuid.uuid4())
    elif source_tp == SPLITTER_TP:
        out_data = producer(meta)
    else:  # Default case
        pre_handle_res = handle_reduce(meta, stage_name='consumer')
        if pre_handle_res is not None:
            out_data = consumer(pre_handle_res)
        else:
            return {}
    return out_data


if __name__ == '__main__':
    port = 8080
    init()
    app.run(debug=True, host='0.0.0.0', port=port)
