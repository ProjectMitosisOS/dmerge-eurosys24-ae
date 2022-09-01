from ctypes import c_int, addressof

a = 12
tmp = c_int(a)
print(hex(id(tmp)))
print(hex(addressof(tmp)))
