import json
import logging
import os
import sys
import uuid
import uvicorn

from fastapi import FastAPI, Request
from fastapi.responses import Response

app = FastAPI()
app_logger = logging.getLogger('app_logger')
app_logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
# handler = logging.FileHandler('app.log')
app_logger.addHandler(handler)

# Env list
ce_specversion = os.environ.get('CE_SPECVERSION', '0.3')


def fill_ce_header(id, ce_specversion, ce_type):
    """
    Fill for the Cloud Event header
    :param id:
    :param ce_specversion:
    :param ce_type:
    :return:
    """
    return {
        "Ce-Id": id,
        "Ce-specversion": ce_specversion,
        "Ce-Type": ce_type,
        "Ce-Source": 'e',
    }


@app.post("/")
async def faas_entry(request: Request):
    payload = await request.body()

    app_logger.info(f'incoming data {payload}')

    response_header = fill_ce_header(id=str(uuid.uuid4()),
                                     ce_specversion=ce_specversion,
                                     ce_type='ceType')

    return Response(content=json.dumps({'d': str(uuid.uuid4())}),
                    headers=response_header,
                    status_code=200, media_type="application/json")


if __name__ == '__main__':
    port = 8080
    workers = int(os.environ.get('WEB_WORKER', '1'))
    uvicorn.run("__main__:app", host="0.0.0.0", port=port, workers=workers)
