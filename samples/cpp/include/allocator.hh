#include <jemalloc/jemalloc.h>
#include <cstdint>
#include <mutex>
#include <functional>

using ptr_t = void *;

class Allocator {
public:
    explicit Allocator(unsigned id) : id(id) {
    }

    inline ptr_t alloc(uint32_t size, int flag = 0) {
        auto ptr = mallocx(size, id | flag);
        return ptr;
    }

    inline void dealloc(ptr_t ptr) { free(ptr); }

    inline void free(ptr_t ptr) {
        dallocx(ptr, id);
    }

private:
    unsigned id;
};
