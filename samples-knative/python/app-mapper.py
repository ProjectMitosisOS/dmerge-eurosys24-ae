import os

from flask import Flask, request, make_response
import uuid
import requests

app = Flask(__name__)

ce_specversion = os.environ.get('CE_SPECVERSION', '0.3')
ce_type = os.environ.get("CE_TYPE", "default")


@app.route('/', methods=['POST'])
def hello_world():
    app.logger.warning(request.data)
    # Respond with another event (optional)
    response = make_response({
        "msg": "Hi from helloworld-python app!!!"
    })
    response.headers["Ce-Id"] = str(uuid.uuid4())
    response.headers["Ce-specversion"] = ce_specversion
    response.headers["Ce-Type"] = ce_type
    response.headers["Ce-Source"] = "knative/eventing/samples/faas"
    return response


@app.route('/trigger')
def start():
    register_url = "http://broker-ingress.knative-eventing.svc.cluster.local/knative-samples/default"
    header = {
        "Ce-Id": str(uuid.uuid4()),
        "Ce-specversion": ce_specversion,
        "Ce-Type": ce_type,
        "Ce-Source": "dev.knative.samples/source",
        "Content-Type": "application/json"
    }

    json = {
        "msg": "Hello World from the curl pod."
    }
    requests.post(url=register_url, json=json, headers=header)
    return make_response({
        "msg": "Echo reply"
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
