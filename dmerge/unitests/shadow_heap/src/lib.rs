#![no_std]

extern crate alloc;

use dmerge::{mitosis, log};

use mitosis::linux_kernel_module;

use dmerge::descriptors::HeapMeta;
use dmerge::KRdmaKit::mem::RMemPhy;
use dmerge::shadow_heap::ShadowHeap;

mod my_syscalls;

use my_syscalls::*;
use mitosis::syscalls::*;
use mitosis::bindings;
use dmerge::mitosis_macros::declare_global;

declare_global!(mac_id, usize);
declare_global!(heap_descriptor, dmerge::descriptors::heap::HeapDescriptor);
declare_global!(mem_pool, crate::mitosis::mem_pools::MemPool);


#[inline]
pub unsafe fn get_heap_descriptor_ref() -> &'static dmerge::descriptors::heap::HeapDescriptor {
    crate::heap_descriptor::get_ref()
}

#[inline]
pub unsafe fn get_heap_descriptor_mut() -> &'static mut dmerge::descriptors::heap::HeapDescriptor {
    crate::heap_descriptor::get_mut()
}

#[inline]
pub unsafe fn get_mem_pool_ref() -> &'static crate::mitosis::mem_pools::MemPool {
    crate::mem_pool::get_ref()
}

#[inline]
pub unsafe fn get_mem_pool_mut() -> &'static mut crate::mitosis::mem_pools::MemPool {
    crate::mem_pool::get_mut()
}

pub fn startup() {
    unsafe {
        crate::heap_descriptor::init(Default::default());
        crate::mac_id::init(0);

        crate::mem_pool::init(mitosis::mem_pools::MemPool::new(12));

    }
}

pub fn end() {
    unsafe {
        crate::heap_descriptor::drop();
        crate::mem_pool::drop();
    };
}

#[allow(dead_code)]
struct Module {
    service: SysCallsService<MySyscallHandler>,
}

impl linux_kernel_module::KernelModule for Module {
    fn init() -> linux_kernel_module::KernelResult<Self> {
        startup();

        Ok(Self {
            service: SysCallsService::<MySyscallHandler>::new()?,
        })
    }
}

impl Drop for Module {
    fn drop(&mut self) {
        end();
        log::info!("drop system call modules");
    }
}

linux_kernel_module::kernel_module!(
    Module,
    author: b"lfm",
    description: b"A kernel module for testing system calls",
    license: b"GPL"
);
