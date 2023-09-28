import json
import logging
import pickle

import requests
from cloudevents.http import from_http, CloudEvent
from fastapi import FastAPI, Request
from fastapi.responses import Response
import sys
import util
from functions import *
import uvicorn

app = FastAPI()
app_logger = logging.getLogger('app_logger')
app_logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
# handler = logging.FileHandler('app.log')
app_logger.addHandler(handler)

# Env list
ce_specversion = os.environ.get('CE_SPECVERSION', '0.3')
WORKFLOW_ID_KEY = 'wf_id'

PING_TP = 'dev.knative.sources.ping'
SPLITTER_TP = 'splitter'
PRODUCER_TP = 'producer'
CONSUMER_TP = 'consumer'
# Mapping from source ce type into (ce handlers, if_waiting)
handler_dispatch = {
    PING_TP: (splitter, False),
    SPLITTER_TP: (producer, False),
    PRODUCER_TP: (consumer, False),
}

next_hop_map = {
    PING_TP: SPLITTER_TP,
    SPLITTER_TP: PRODUCER_TP,
    PRODUCER_TP: CONSUMER_TP,
}


@app.post('/hello')
async def hello(request: Request):
    response_header = util.fill_ce_header(id=str(uuid.uuid4()),
                                          ce_specversion=ce_specversion,
                                          ce_type='splitter')
    return Response(content=pickle.dumps({'meta': 'sink'}),
                    headers=response_header)


@app.post('/')
async def faas_entry(request: Request):
    payload = await request.body()

    is_pingpong = request.headers['Ce-Source'] == 'ping-pong'
    if is_pingpong:
        unmarshaller = None
    else:
        # unmarshaller = None
        unmarshaller = pickle.loads
    event = from_http(request.headers, payload, data_unmarshaller=unmarshaller)

    data, ce_type = handle_ce(event)

    response_header = util.fill_ce_header(id=str(uuid.uuid4()),
                                          ce_specversion=ce_specversion,
                                          ce_type=ce_type)
    response_header.update({
        "Content-Type": "application/octet-stream"
    })
    if ce_type in next_hop_map.keys():
        next_hop = next_hop_map[ce_type]

        next_response = requests.post(f'http://{next_hop}-00001-private/',
                                      data=pickle.dumps(data),
                                      headers=response_header)
        return next_response.json()
    else:
        return Response(content=json.dumps(data),
                        headers=response_header)


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


def handle_reduce(meta, stage_name):
    stage = stage_name
    wf_id = meta[WORKFLOW_ID_KEY]

    stream_cnt = int(os.environ.get(upstream_num_env_str, "1"))
    """
    cur_stage_info as below:
    {
        wf_id: [event1, event2]
    },
    """
    if stage not in upstream_info.keys():
        upstream_info[stage] = {}
    cur_stage_info = dict(upstream_info[stage])
    if wf_id not in cur_stage_info.keys():
        cur_stage_info[wf_id] = [meta]
    else:
        cur_stage_info[wf_id].append(meta)
    # write back
    upstream_info[stage][wf_id] = cur_stage_info[wf_id]

    if len(cur_stage_info[wf_id]) >= stream_cnt:  # TODO: Shall we guarantee the contention ?
        # Finish reduce
        app_logger.debug(f'Finish reduce at stage {stage}. upstream_info {upstream_info}')
        upstream_info[stage].pop(wf_id)
        return cur_stage_info[wf_id]
    else:
        app_logger.debug(
            f'Wait for next at stage {stage}. upstream_info {upstream_info}, Upstream cnt {stream_cnt}')
        return None


def handle_ce(event: CloudEvent):
    """
    - The `none` ce type will be ignored at last stage.
    :param event:
    :return:
    """
    meta = event.data
    source_tp = event['type']
    (handler, if_wait) = handler_dispatch.get(source_tp, (default_handler, False))
    ce_type = os.environ.get("CE_TYPE", "none")

    if if_wait:
        if type(meta) == dict and len(meta) > 0:
            pre_handle_res = handle_reduce(meta, stage_name=handler.__name__)
            if pre_handle_res is not None:
                return handler(pre_handle_res), ce_type
        else:
            app_logger.error(f"not supposed to be here. source tp: {source_tp}, "
                             f"handler name: {handler.__name__}")
            return {}, 'none'
    else:
        return handler(meta), ce_type
    return {}, 'none'


if __name__ == '__main__':
    workers = int(os.environ.get('WEB_WORKER', '1'))
    app_logger.info('port at {}')
    uvicorn.run("__main__:app", host="0.0.0.0", port=8080, workers=workers)
