from bindings import *
addr = 0x4ffff5a00000

sd = sopen()
res = syscall_connect_session(
    sd,
    "fe80:0000:0000:0000:ec0d:9a03:00c8:491c", 0, 0)
print("connect res %d" % res)

# res = call_pull(sd=sd, hint=1, machine_id=0)
# test_mem()  # TODO: Why it does not segment fault ?

# print(my_read_ptr(addr))
