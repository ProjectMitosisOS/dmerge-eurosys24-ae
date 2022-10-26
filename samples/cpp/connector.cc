#include "../../dmerge-user-libs/include/syscall.h"
#include "../include/allocator.hh"


int
main() {
    int sd = sopen();
    int res = call_connect_session(sd, "fe80:0000:0000:0000:248a:0703:009c:7ca0",
                         0, 0);

    std::cout << std::dec << "connect res:" << res << std::endl;
    std::cout << "end" << std::endl;
    return 0;
}
