#include <assert.h>
#include "../../dmerge-user-libs/include/syscall.h"
#include "include/allocator.hh"

int
main()
{
    int sd = sopen();
    assert(sd != 0);

    call_peak(sd);
    return 0;
}
