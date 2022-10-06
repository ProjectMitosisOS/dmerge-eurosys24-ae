use std::borrow::BorrowMut;
use libc::{c_char, c_int, c_uint, c_void, memset, size_t};

use std::ptr::{null, null_mut};
use jemalloc_sys::*;
use std::cell::RefCell;
use std::intrinsics::{likely, unlikely};
use std::mem::size_of;
use std::sync::{Mutex};
use thread_local::ThreadLocal;

type c_bool = c_int;

use std::collections::HashMap;

lazy_static! {
    pub static ref ALLOC: Mutex<AllocatorMaster> = Mutex::new(Default::default());
}

pub struct Allocator {
    id: c_int,
}

impl Allocator {
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
    thread_allocator: ThreadLocal<Allocator>,
}

impl Default for AllocatorMaster {

    fn default() -> Self {
        Self {
            start_addr: 0 as *mut c_char,
            end_addr: 0 as *mut c_char,
            heap_top: 0 as *mut c_char,
            hooks: Default::default(),
            thread_allocator: Default::default(),
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
                alloc: Some(AllocatorMaster::extent_alloc_hook),
                dalloc: Some(AllocatorMaster::extent_dalloc_hook),
                destroy: Some(AllocatorMaster::extent_destroy_hook),
                commit: Some(AllocatorMaster::extent_commit_hook),
                decommit: Some(AllocatorMaster::extent_decommit_hook),
                purge_lazy: Some(AllocatorMaster::extent_purge_lazy_hook),
                purge_forced: Some(AllocatorMaster::extent_purge_forced_hook),
                split: Some(AllocatorMaster::extent_split_hook),
                merge: Some(AllocatorMaster::extent_merge_hook),
            },
            thread_allocator: Default::default(),
        }
    }

    pub unsafe fn get_thread_allocator(&mut self) -> &Allocator {
        if unlikely(self.thread_allocator.get().is_some()) {
            self.thread_allocator = ThreadLocal::new();
        }
        self.thread_allocator.get().unwrap()
    }

    pub unsafe fn get_allocator(&self) -> Allocator {
        let (mut arena_id, mut cache_id) = (0, 0);

        let mut sz = size_of::<usize>();
        let new_hooks = &self.hooks;
        let _ = mallctl("arenas.create".as_ptr() as _,
                        &mut arena_id as *mut usize as _,
                        &mut sz as *mut usize as _,
                        new_hooks as *const extent_hooks_t as _,
                        size_of::<*mut extent_hooks_t>());

        let _ = mallctl("tcache.create".as_ptr() as _,
                        &mut cache_id as *mut usize as _,
                        &mut sz as *mut usize as _,
                        null_mut(),
                        0);
        return Allocator::create(MALLOCX_ARENA(arena_id) | MALLOCX_TCACHE(cache_id));
    }
}

impl AllocatorMaster {
    fn total_managed_mem(&self) -> u64 {
        self.end_addr as u64 - self.start_addr as u64
    }
}

impl AllocatorMaster {
    #[allow(dead_code)]
    unsafe extern "C" fn extent_alloc_hook(
        extent_hooks: *mut extent_hooks_t,
        new_addr: *mut c_void,
        size: size_t,
        alignment: size_t,
        zero: *mut c_bool,
        commit: *mut c_bool,
        arena_ind: c_uint,
    ) -> *mut c_void {
        let mut alloc_master = ALLOC.lock()
            .expect("fail to get allocator master");

        let mut ret = alloc_master.heap_top as size_t;
        if ret % alignment != 0 {
            ret = ret + (alignment - ret % alignment)
        }
        if ret + size >= alloc_master.end_addr as size_t {
            println!("exceed heap size. Want sz:{}", size);
            return null_mut();
        }

        alloc_master.heap_top = (ret + size) as *mut c_char;
        if *zero != 0 {
            let _ = memset(ret as _, 0, size);
        }
        return ret as _;
    }

    #[allow(dead_code)]
    unsafe extern "C" fn extent_dalloc_hook(
        extent_hooks: *mut extent_hooks_t,
        addr: *mut c_void,
        size: size_t,
        committed: c_bool,
        arena_ind: c_uint,
    ) -> c_bool {
        return 0;
    }

    #[allow(dead_code)]
    unsafe extern "C" fn extent_destroy_hook(
        extent_hooks: *mut extent_hooks_t,
        addr: *mut c_void,
        size: size_t,
        committed: c_bool,
        arena_ind: c_uint,
    ) {
        return;
    }

    #[allow(dead_code)]
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

    #[allow(dead_code)]
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

    #[allow(dead_code)]
    unsafe extern "C" fn extent_purge_lazy_hook(
        extent_hooks: *mut extent_hooks_t,
        addr: *mut c_void,
        size: size_t,
        offset: size_t,
        length: size_t,
        arena_ind: c_uint,
    ) -> c_bool {
        return 0;
    }

    #[allow(dead_code)]
    unsafe extern "C" fn extent_purge_forced_hook(
        extent_hooks: *mut extent_hooks_t,
        addr: *mut c_void,
        size: size_t,
        offset: size_t,
        length: size_t,
        arena_ind: c_uint,
    ) -> c_bool {
        return 0;
    }

    #[allow(dead_code)]
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

    #[allow(dead_code)]
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
}

unsafe impl Sync for AllocatorMaster {}

unsafe impl Send for AllocatorMaster {}