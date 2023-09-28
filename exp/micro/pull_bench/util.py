import time

from bindings import *


def fill_gid(gid):
    new_mac_id_parts = []
    for part in gid.split(":"):
        new_part = ":".join([str(hex(int(i, 16)))[2:].zfill(4) for i in part.split(".")])
        new_mac_id_parts.append(new_part)
    new_mac_id = ":".join(new_mac_id_parts)
    return new_mac_id


def cur_tick_ms():
    return int(round(time.time() * 1000))


def cur_tick_us():
    return int(round(time.time() * 1000000))


def pull(sd, mac_id, hint, eager_fetch):
    return call_pull(sd=sd, hint=hint,
                     machine_id=mac_id, eager_fetch=eager_fetch)


def fetch(target):
    if type(target) == list:
        return [id_deref(target_id, None) for target_id in target]
    else:
        return id_deref(target, None)


def push(sd, nic_id, peak_addr):
    gid, mac_id = syscall_get_gid(sd=sd, nic_idx=nic_id)
    gid = fill_gid(gid)
    hint = call_register(sd=sd, peak_addr=peak_addr)
    return gid, mac_id, hint
