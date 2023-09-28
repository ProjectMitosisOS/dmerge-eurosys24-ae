import json


def dump_file_to_kv(path):
    with open(path) as f:
        content = json.dumps(f.readlines())
        return content