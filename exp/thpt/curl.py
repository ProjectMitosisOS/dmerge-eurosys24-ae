import requests

ce_type = 'splitter'
headers = {
    'Ce-Id': '536808d3-88be-4077-9d7a-a3f162705f79',
    'Ce-Specversion': '1.0',
    'Ce-Type': 'dev.knative.sources.ping',
    'Ce-Source': 'ping-pong',
    'Content-Type': 'application/json',
}

ext_response = requests.post(f"http://localhost/hello",
                             headers=headers)

print(ext_response)
