from cloudevents.http import from_http, CloudEvent
from flask import Flask, request, make_response

import util
from functions import *

app = Flask(__name__)
app.logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Env list
ce_specversion = os.environ.get('CE_SPECVERSION', '0.3')
ce_type = os.environ.get("CE_TYPE", "default")
WORKFLOW_ID_KEY = 'wf_id'

PING_TP = 'dev.knative.sources.ping'
SPLITTER_TP = 'splitter'
PRODUCER_TP = 'producer'
CONSUMER_TP = 'consumer'
# Mapping from source ce type into (ce handlers, if_waiting)
handler_dispatch = {
    PING_TP: (splitter, False),
    SPLITTER_TP: (producer, False),
    PRODUCER_TP: (consumer, True),
    CONSUMER_TP: (sink, True)
}


# Thanks the CE python SDK https://github.com/cloudevents/sdk-python
@app.route('/', methods=['POST'])
def faas_entry():
    event = from_http(request.headers, request.get_data())
    data = handle_ce(event)
    response = make_response(data)
    ceType = ce_type
    response.headers = util.fill_ce_header(id=str(uuid.uuid4()),
                                           ce_specversion=ce_specversion,
                                           ce_type=ceType,
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


def handle_reduce(meta, stage_name):
    from flask import current_app
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
    (handler, if_wait) = handler_dispatch.get(source_tp, (default_handler, False))

    if if_wait:
        if type(meta) == dict and len(meta) > 0:
            pre_handle_res = handle_reduce(meta, stage_name=handler.__name__)
            if pre_handle_res is not None:
                return handler(pre_handle_res)
        else:
            return {}
    else:
        return handler(meta)
    return {}


if __name__ == '__main__':
    port = 8080
    app.run(debug=True, host='0.0.0.0', port=port)
