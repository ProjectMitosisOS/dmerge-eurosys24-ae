#include "../../../dmerge-user-libs/include/syscall.h"
#include "gflags/gflags.h"
#include <cassert>
#include <iostream>
#include <string>
#include <vector>
#include <set>
#include <sstream>

// ./full_connector --machine_ids=7,9,12
DEFINE_int64(nic_id, 0, "nic idx. Should be align with gid");
DEFINE_string(machine_ids, "6,7,9", "all of the machines in the cluster");

static std::vector <std::pair<size_t, std::string>> mac_ids = {
        {1,  "fe80:0000:0000:0000:ec0d:9a03:00ca:2f4c"},
        {2,  "fe80:0000:0000:0000:ec0d:9a03:0078:6416"},
        {3,  "fe80:0000:0000:0000:ec0d:9a03:00ca:31d8"},
        {4,  "fe80:0000:0000:0000:ec0d:9a03:0078:647e"},
        {5,  "fe80:0000:0000:0000:ec0d:9a03:00c8:491c"},
        {6,  "fe80:0000:0000:0000:248a:0703:009c:7ca0"},
        {7,  "fe80:0000:0000:0000:248a:0703:009c:7ca8"},
        {9,  "fe80:0000:0000:0000:248a:0703:009c:7e00"},
        {12, "fe80:0000:0000:0000:ec0d:9a03:0078:64a6"},
        {14, "fe80:0000:0000:0000:ec0d:9a03:0078:645e"},
};

std::set<size_t> toMachineSet(const std::string& inputString) {
    std::set<size_t> outputSet;
    std::stringstream ss(inputString);
    std::string token;
    while (std::getline(ss, token, ',')) {
        int number = std::stoi(token);
        outputSet.insert(number);
    }
    return outputSet;
}
void connect_all(const std::set<size_t> &target_set, const int nic_id) {
    const int sd = sopen();

    for (auto p: mac_ids) {
        size_t machine_id = p.first;
        if (target_set.count(machine_id) ) {
            const char *remote_gid = p.second.c_str();
            int res = call_connect_session(sd, remote_gid, machine_id, nic_id);
            std::cout << std::dec << "@" << machine_id << " connect res:" << res << std::endl;
            assert(res == 0);
        }

    }
}

int
main(int argc, char *argv[]) {
    gflags::ParseCommandLineFlags(&argc, &argv, true);
    auto machines = toMachineSet(FLAGS_machine_ids);
    connect_all(machines,FLAGS_nic_id);
    return 0;
}
