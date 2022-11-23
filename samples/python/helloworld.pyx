# distutils: language=c++
import ctypes

#  python setup.py build_ext --inplace
def fib(n):
    """Print the Fibonacci series up to n."""
    a, b = 0, 1
    while b < n:
        print(b)
        a, b = b, a + b


cdef extern from "math.h":
    # It must be cdef type
    cpdef double sin(double x)

from libcpp.vector cimport vector
from libcpp.string cimport string

#from libc.stdio cimport printf

cpdef print_vect(string content):
    cdef vector[int] vect
    cdef int i
    for i in range(10):
        vect.push_back(i)
    for i in vect:
        #printf("%d",vect[i])
        print(vect[i])
    for i in content:
        #printf("%d",vect[i])
        print(i)

def primes(int nb_primes):
    cdef int n, i, len_p
    cdef int p[1000]

    if nb_primes > 1000:
        nb_primes = 1000

    len_p = 0  # The current number of elements in p.
    n = 2
    while len_p < nb_primes:
        # Is n prime?
        for i in p[:len_p]:
            if n % i == 0:
                break

        # If no break occurred in the loop, we have a prime.
        else:
            p[len_p] = n
            len_p += 1
        n += 1

    # Let's copy the result into a Python list:
    result_as_list = [prime for prime in p[:len_p]]
    return result_as_list


cdef extern from "string.h":
    char * strstr(const char *haystack, const char *needle)

cpdef cstrstr():
    cdef char * data = "hfvcakdfagbcffvschvxcdfgccbcfhvgcsnfxjh"
    cdef char * pos = strstr(needle='akd', haystack=data)
    return pos is not NULL



