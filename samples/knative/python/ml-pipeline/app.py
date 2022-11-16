import os

from flask import Flask, request, make_response
import uuid
import requests
import util

app = Flask(__name__)

ce_specversion = os.environ.get('CE_SPECVERSION', '0.3')
ce_type = os.environ.get("CE_TYPE", "default")


@app.route('/', methods=['POST'])
def hello_world():
    app.logger.warning(request.data)
    response = make_response({
        "msg": "Hello world!"
    })
    response.headers = util.fill_ce_header(id=str(uuid.uuid4()),
                                           ce_specversion=ce_specversion,
                                           ce_type=ce_type,
                                           ce_source="ml-pipeline")
    app.logger.warning(response.headers)
    return response


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
