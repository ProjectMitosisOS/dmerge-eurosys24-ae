from flask import Flask, request, make_response
import uuid
import requests

app = Flask(__name__)


@app.route('/', methods=['POST'])
def hello_world():
    app.logger.warning(request.data)
    # Respond with another event (optional)
    response = make_response({
        "msg": "Hi from helloworld-python app!!!"
    })
    response.headers["Ce-Id"] = str(uuid.uuid4())
    response.headers["Ce-specversion"] = "0.3"
    response.headers["Ce-Source"] = "knative/eventing/samples/hello-world"
    response.headers["Ce-Type"] = "dev.knative.samples.replytosink"
    return response


@app.route('/start')
def start():
    register_url = "http://broker-ingress.knative-eventing.svc.cluster.local/knative-samples/default"
    header = {
        "Ce-Id": str(uuid.uuid4()),
        "Ce-specversion": "0.3",
        "Ce-Type": "dev.knative.samples.helloworld",
        "Ce-Source": "dev.knative.samples/source",
        "Content-Type": "application/json"
    }

    json = {
        "msg": "Hello World from the curl pod."
    }
    requests.post(url=register_url, json=json, headers=header)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
