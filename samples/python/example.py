#! /usr/bin/env python

from fcntl import ioctl
import socket
import struct
import sys

sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
try:
    ip=ioctl(sock.fileno(),0x8915,struct.pack('64s','eth0'))
    ip=socket.inet_ntoa(ip[20:24])
    print(ip)
except:
    print(sys.exc_info())
