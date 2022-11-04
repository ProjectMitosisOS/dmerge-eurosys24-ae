use std::intrinsics::{likely, unlikely};
use std::mem::size_of;
use std::ptr::{null_mut};
use core::alloc::{AllocError, Allocator};
use core::ptr::NonNull;

use core::alloc::Layout;
use crate::get_global_allocator_master_mut;
use jemalloc_sys::*;
use libc::{c_char, c_int, c_uint, c_void, memset, size_t};

type c_bool = c_int;

#[derive(Default)]
pub struct JeAllocator {
    id: c_int,
}

impl JeAllocator {
    pub fn create(id: c_int) -> Self {
        Self { id }
    }

    #[inline]
    pub unsafe fn alloc(&self, size: size_t, flag: c_int) -> *mut c_void {
        mallocx(size, self.id | flag)
    }

    #[inline]
    pub unsafe fn dealloc(&self, ptr: *mut c_void) {
        free(ptr);
    }

    #[inline]
    pub unsafe fn free(&self, ptr: *mut c_void) {
        dallocx(ptr, self.id as c_int);
    }
}

pub struct AllocatorMaster {
    pub start_addr: *mut c_char,
    pub end_addr: *mut c_char,

    heap_top: *mut c_char,
    hooks: extent_hooks_t,
    thread_allocator: Option<JeAllocator>,
    lock: usize,
}

impl Default for AllocatorMaster {
    fn default() -> Self {
        Self {
            start_addr: 0 as *mut c_char,
            end_addr: 0 as *mut c_char,
            heap_top: 0 as *mut c_char,
            hooks: Default::default(),
            thread_allocator: Default::default(),
            lock: 0,
        }
    }
}


impl AllocatorMaster {
    pub fn init(mem_addr: *mut c_char, mem_size: u64) -> Self {
        AllocatorMaster {
            start_addr: mem_addr,
            end_addr: ((mem_addr as u64) + mem_size) as _,
            heap_top: mem_addr,
            hooks: extent_hooks_s {
                alloc: Some(extent_alloc_hook),
                dalloc: Some(extent_dalloc_hook),
                destroy: Some(extent_destroy_hook),
                commit: Some(extent_commit_hook),
                decommit: Some(extent_decommit_hook),
                purge_lazy: Some(extent_purge_lazy_hook),
                purge_forced: Some(extent_purge_forced_hook),
                split: Some(extent_split_hook),
                merge: Some(extent_merge_hook),
            },
            thread_allocator: Default::default(),
            lock: 0,
        }
    }

    pub unsafe fn get_thread_allocator(&mut self) -> &JeAllocator {
        if unlikely(self.thread_allocator.is_none()) {
            self.thread_allocator = Some(self.get_allocator());
        }
        self.thread_allocator.as_ref().expect("error get thread allocator")
    }

    pub unsafe fn get_allocator(&self) -> JeAllocator {
        {
            let _ = std::sync::Mutex::new(self.lock)
                .lock()
                .unwrap();
            if self.total_managed_mem() == 0 {
                println!("err, total mem is 0");
            }
        }
        let (mut arena_id, mut cache_id): (c_uint, c_uint) = (0, 0);

        let mut sz = size_of::<c_uint>();
        let new_hooks = &self.hooks as *const extent_hooks_t;
        // Attention!!!: The command name must end with '\0'
        let _ = mallctl(
            "arenas.create\0".as_ptr() as _,
            &mut arena_id as *mut c_uint as _,
            &mut sz as *mut usize as _,
            &new_hooks as *const *const extent_hooks_t as _,
            size_of::<*const extent_hooks_t>());

        let _ = mallctl(
            "tcache.create\0".as_ptr() as _,
            &mut cache_id as *mut c_uint as _,
            &mut sz as *mut usize as _,
            null_mut(),
            0);
        JeAllocator::create(MALLOCX_ARENA(arena_id as _) |
            MALLOCX_TCACHE(cache_id as _))
    }
}

impl AllocatorMaster {
    #[allow(dead_code)]
    fn total_managed_mem(&self) -> u64 {
        self.end_addr as u64 - self.start_addr as u64
    }
}

#[allow(dead_code, unused_variables)]
unsafe extern "C" fn extent_alloc_hook(
    extent_hooks: *mut extent_hooks_t,
    new_addr: *mut c_void,
    size: size_t,
    alignment: size_t,
    zero: *mut c_bool,
    commit: *mut c_bool,
    arena_ind: c_uint,
) -> *mut c_void {
    let mut alloc_master = crate::get_global_allocator_master_mut();
    let _ = std::sync::Mutex::new(alloc_master.lock)
        .lock()
        .unwrap();
    let mut ret = alloc_master.heap_top as size_t;
    if ret % alignment != 0 {
        ret = ret + (alignment - ret % alignment)
    }
    if ret + size >= alloc_master.end_addr as size_t {
        println!("exceed heap size. Want sz: {}", size);
        return null_mut();
    }

    alloc_master.heap_top = (ret + size) as *mut c_char;
    if (*zero & 0x01) != 0 {
        let _ = memset(ret as _, 0, size);
    }
    return ret as _;
}

#[allow(dead_code, unused_variables)]
unsafe extern "C" fn extent_dalloc_hook(
    extent_hooks: *mut extent_hooks_t,
    addr: *mut c_void,
    size: size_t,
    committed: c_bool,
    arena_ind: c_uint,
) -> c_bool {
    return 1;
}

#[allow(dead_code, unused_variables)]
unsafe extern "C" fn extent_destroy_hook(
    extent_hooks: *mut extent_hooks_t,
    addr: *mut c_void,
    size: size_t,
    committed: c_bool,
    arena_ind: c_uint,
) {
    return;
}

#[allow(dead_code, unused_variables)]
unsafe extern "C" fn extent_commit_hook(
    extent_hooks: *mut extent_hooks_t,
    addr: *mut c_void,
    size: size_t,
    offset: size_t,
    length: size_t,
    arena_ind: c_uint,
) -> c_bool {
    return 0;
}

#[allow(dead_code, unused_variables)]
unsafe extern "C" fn extent_decommit_hook(
    extent_hooks: *mut extent_hooks_t,
    addr: *mut c_void,
    size: size_t,
    offset: size_t,
    length: size_t,
    arena_ind: c_uint,
) -> c_bool {
    return 0;
}

#[allow(dead_code, unused_variables)]
unsafe extern "C" fn extent_purge_lazy_hook(
    extent_hooks: *mut extent_hooks_t,
    addr: *mut c_void,
    size: size_t,
    offset: size_t,
    length: size_t,
    arena_ind: c_uint,
) -> c_bool {
    return 1;
}

#[allow(dead_code, unused_variables)]
unsafe extern "C" fn extent_purge_forced_hook(
    extent_hooks: *mut extent_hooks_t,
    addr: *mut c_void,
    size: size_t,
    offset: size_t,
    length: size_t,
    arena_ind: c_uint,
) -> c_bool {
    return 1;
}

#[allow(dead_code, unused_variables)]
unsafe extern "C" fn extent_split_hook(
    extent_hooks: *mut extent_hooks_t,
    addr: *mut c_void,
    size: size_t,
    size_a: size_t,
    size_b: size_t,
    committed: c_bool,
    arena_ind: c_uint,
) -> c_bool {
    return 0;
}

#[allow(dead_code, unused_variables)]
unsafe extern "C" fn extent_merge_hook(
    extent_hooks: *mut extent_hooks_t,
    addr_a: *mut c_void,
    size_a: size_t,
    addr_b: *mut c_void,
    size_b: size_t,
    committed: c_bool,
    arena_ind: c_uint,
) -> c_bool {
    return 0;
}

unsafe impl Sync for AllocatorMaster {}

unsafe impl Send for AllocatorMaster {}


#[derive(Copy, Clone, Default, Debug)]
pub struct JemallocAllocator;

unsafe impl Allocator for JemallocAllocator {
    fn allocate(&self, layout: Layout) -> Result<NonNull<[u8]>, AllocError> {
        match layout.size() {
            0 => Ok(NonNull::slice_from_raw_parts(layout.dangling(), 0)),
            // SAFETY: `layout` is non-zero in size,
            size => unsafe {
                let allocator = get_global_allocator_master_mut()
                    .get_thread_allocator();
                let raw_ptr = allocator.alloc(size as _, 0) as *mut u8;
                let ptr = NonNull::new(raw_ptr).ok_or(AllocError)?;
                Ok(NonNull::slice_from_raw_parts(ptr, size))
            }
        }
    }

    unsafe fn deallocate(&self, ptr: NonNull<u8>, _layout: Layout) {
        let allocator = get_global_allocator_master_mut()
            .get_thread_allocator();
        allocator.dealloc(ptr.as_ptr() as *mut c_void);
    }
}