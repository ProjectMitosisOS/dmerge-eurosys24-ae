import os

from flask import Flask, request, make_response
import uuid
import requests
import util

app = Flask(__name__)

ce_specversion = os.environ.get('CE_SPECVERSION', '0.3')
ce_type = os.environ.get("CE_TYPE", "default")
if_debug = os.environ.get("DEBUG", True)


@app.route('/', methods=['POST'])
def hello_world():
    app.logger.debug(dict(request.headers))
    response = make_response({
        "msg": "Hello world!"
    })
    response.headers = util.fill_ce_header(id=str(uuid.uuid4()),
                                           ce_specversion=ce_specversion,
                                           ce_type=ce_type,
                                           ce_source="ml-pipeline")
    return response


if __name__ == '__main__':
    app.run(debug=if_debug, host='0.0.0.0', port=8080)
