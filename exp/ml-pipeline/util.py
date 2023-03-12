import time
from bindings import *


def fill_gid(gid):
    new_mac_id_parts = []
    for part in gid.split(":"):
        new_part = ":".join([str(hex(int(i, 16)))[2:].zfill(4) for i in part.split(".")])
        new_mac_id_parts.append(new_part)
    new_mac_id = ":".join(new_mac_id_parts)
    return new_mac_id


def fill_ce_header(id, ce_specversion, ce_type, ce_source):
    """
    Fill for the Cloud Event header
    :param id:
    :param ce_specversion:
    :param ce_type:
    :param ce_source:
    :return:
    """
    return {
        "Ce-Id": id,
        "Ce-specversion": ce_specversion,
        "Ce-Type": ce_type,
        "Ce-Source": ce_source,
    }


def cur_tick_ms():
    return int(round(time.time() * 1000))


def pull(sd, gid, mac_id, hint, nic_id, need_connect=True):
    if need_connect:
        res = syscall_connect_session(
            sd, gid, machine_id=mac_id, nic_id=nic_id)
        assert res == 0
    call_pull(sd=sd, hint=hint, machine_id=mac_id)


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
