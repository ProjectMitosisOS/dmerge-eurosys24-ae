// main.cpp
//#include <python3.10/Python.h>
#include <Python.h>

int main(int argc, char *argv[]) {
    Py_Initialize();
    PyRun_SimpleString("from time import time,ctime\n"
                       "print('Today is',ctime(time()))\n"
                       "start = time() * 1000000\n"
                       "for i in range(50000):\n"
                       "    num = i * i\n"
                       "end = time() * 1000000\n"
                       "print('passed %d us' % (end - start))\n"
    );
    Py_Finalize();
    return 0;
}