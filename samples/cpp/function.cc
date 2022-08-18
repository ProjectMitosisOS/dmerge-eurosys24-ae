#include <assert.h>
#include <unistd.h>
#include "../../dmerge-user-libs/include/syscall.h"
#include "include/allocator.hh"
//#include <jemalloc/jemalloc.h>

int
main()
{
    int sd = sopen();
    assert(sd != 0);

    call_peak(sd);
    return 0;
}
