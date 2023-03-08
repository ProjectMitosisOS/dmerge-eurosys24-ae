#include "common.hh"


// producer
int
main() {
    uint64_t base_addr = BASE;

    base_addr += OFFSET;
    (*(int *) base_addr) = 4090;
    std::cout << std::dec << (uint64_t) (*(int *) base_addr) << "\n";

    int sd = sopen();
    char gid[49];
    size_t machine_id[1];
    int res = call_get_mac_id(sd,0, gid, machine_id);

    printf("gid: %s\n", gid);
    int heap_id = call_register(sd, (uint64_t) base_addr);
    res = *(int *) base_addr;

    for(int i = 0 ;i < 10; ++i) {
        sleep(1);
    }
    return 0;
}
