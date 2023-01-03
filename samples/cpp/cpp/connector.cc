#include "../../../dmerge-user-libs/include/syscall.h"
#include "gflags/gflags.h"
#include <cassert>
#include <iostream>


DEFINE_string(gid, "fe80:0000:0000:0000:248a:0703:009c:7ca0", "connect gid");

DEFINE_int64(mac_id, 0, "machine id");
DEFINE_int64(nic_id, 0, "nic idx. Should be align with gid");

int
main(int argc, char *argv[]) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);

    int sd = sopen();
    assert(sd != 0);

    int res = call_connect_session(sd, FLAGS_gid.c_str(), FLAGS_mac_id, FLAGS_nic_id);

    std::cout << std::dec << "connect res:" << res << std::endl;
    std::cout << "end" << std::endl;
    return 0;
}
