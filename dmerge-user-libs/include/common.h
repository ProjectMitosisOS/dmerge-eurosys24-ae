//#include <stdint.h>

enum LibMITOSISCmd {
    Register = 0,
    Pull = 1,
    ConnectSession = 3,
    GetMacID = 4,
};

typedef struct {
    unsigned int machine_id; // should not be zero!
    unsigned int nic_id; // nic idx according to gid
    const char *gid;
} connect_req_t;

typedef struct {
    unsigned long long heap_base;
} register_req_t;

typedef struct {
    unsigned int heap_hint;
    unsigned int machine_id;
} pull_req_t;

typedef struct {
    unsigned int nic_idx;
    const char *mac_id;
} get_mac_id_req_t;