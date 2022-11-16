import redis_client


def splitter(meta):
    out_data = meta.copy()
    redis_client.put('foo', 'bar')

    out_data['key'] = 'foo'
    return out_data


def trainer(meta):
    out_data = meta.copy()
    redis_client.put('trainer', 'java')

    out_data['kkk'] = 'trainer'
    return out_data


def reduce(meta):
    out_data = meta.copy()
    out_data['data'] = {
        'key': redis_client.get(meta['key']),
        'kkk': redis_client.get(meta['kkk'])
    }

    return out_data
