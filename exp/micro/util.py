import os
import random
import string
import time

from bindings import *

PROTOCOL = os.environ.get('PROTOCOL', 'S3')

SD = sopen() if PROTOCOL in ['DMERGE', 'DMERGE_PUSH'] else 0
eager_fetch = 0
import redis

redis_client = redis.Redis(host='redis', port=6379, password='redis')


def redis_put(k, v):
    redis_client.set(k, v)


def redis_get(k):
    return redis_client.get(k)


def random_string(length=10):
    letters = string.ascii_lowercase
    result = ''.join(random.choice(letters) for i in range(length))
    return result


def reduce_profile(profile_dicts):
    res_dic = {}
    for _, p in profile_dicts.items():
        if isinstance(p, dict):
            for key, value in p.items():
                if key in res_dic.keys():
                    res_dic[key] += value
                else:
                    res_dic[key] = value
    return res_dic


def fill_gid(gid):
    new_mac_id_parts = []
    for part in gid.split(":"):
        new_part = ":".join([str(hex(int(i, 16)))[2:].zfill(4) for i in part.split(".")])
        new_mac_id_parts.append(new_part)
    new_mac_id = ":".join(new_mac_id_parts)
    return new_mac_id


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
        "Ce-Source": str(cur_tick_ms()),
    }


def cur_tick_ms():
    return int(round(time.time() * 1000))


def pull(mac_id, hint):
    return call_pull(sd=SD, hint=hint,
                     machine_id=mac_id, eager_fetch=eager_fetch)


def fetch(target):
    if type(target) == list:
        return [id_deref(target_id, None) for target_id in target]
    else:
        return id_deref(target, None)


def push(nic_id, peak_addr):
    gid, mac_id = syscall_get_gid(sd=SD, nic_idx=nic_id)
    gid = fill_gid(gid)
    hint = call_register(sd=SD, peak_addr=peak_addr)
    return gid, mac_id, hint
