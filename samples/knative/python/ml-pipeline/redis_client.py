import redis
import json

pool = redis.ConnectionPool(host='redis', port=6379, password='redis')


def put(key, content):
    redis_cli = redis.Redis(connection_pool=pool)
    redis_cli.set(key, content)


def get(key):
    redis_cli = redis.Redis(connection_pool=pool)
    return redis_cli.get(key).decode('utf8')


def dump_file_to_kv(path):
    """
    Dump the file content into KV store in json format
    :param path:
    :return:
    """
    with open(path) as f:
        content = json.dumps(f.readlines())
        put(path, content)


def read_file_from_kv(path):
    """
    Read and output as string list
    :param path: path is also the key in the KV store
    :return:
    """
    return json.loads(get(path))
