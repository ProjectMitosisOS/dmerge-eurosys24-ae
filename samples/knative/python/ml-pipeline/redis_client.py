import redis

pool = redis.ConnectionPool(host='redis', port=6379, password='redis')


def put(key, content):
    redis_cli = redis.Redis(connection_pool=pool)
    redis_cli.set(key, content)


def get(key):
    redis_cli = redis.Redis(connection_pool=pool)
    return redis_cli.get(key).decode('utf8')
