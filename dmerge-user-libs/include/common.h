//#include <stdint.h>

enum LibMITOSISCmd {
    Register = 0,
    Pull = 1,
    ConnectSession = 3,
    GetMacID = 4,
    RegisterRemote = 5,
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
    bool eager_fetch;
} pull_req_t;

typedef struct {
    unsigned int nic_idx;
    const char *gid;
    size_t *machine_id;
} get_mac_id_req_t;

typedef struct {
    unsigned long long heap_base;
    unsigned int machine_id;    /* Remote machine id */
} register_remote_req_t;