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
use dmerge::mitosis::startup::end_instance;
use dmerge::mitosis_macros::declare_global;
use crate::mitosis::startup::start_instance;

declare_global!(heap_descriptor, dmerge::descriptors::heap::HeapDescriptor);

declare_global!(
    sh_service,
    dmerge::shadow_heap::ShadowHeapService
);


#[inline]
pub unsafe fn get_heap_descriptor_ref() -> &'static dmerge::descriptors::heap::HeapDescriptor {
    crate::heap_descriptor::get_ref()
}

#[inline]
pub unsafe fn get_heap_descriptor_mut() -> &'static mut dmerge::descriptors::heap::HeapDescriptor {
    crate::heap_descriptor::get_mut()
}

#[inline]
pub unsafe fn get_shs_ref() -> &'static dmerge::shadow_heap::ShadowHeapService {
    crate::sh_service::get_ref()
}

#[inline]
pub unsafe fn get_shs_mut() -> &'static mut dmerge::shadow_heap::ShadowHeapService {
    crate::sh_service::get_mut()
}

pub fn startup() {
    unsafe {
        crate::heap_descriptor::init(Default::default());
        crate::sh_service::init(Default::default());

        {
            let mut config: mitosis::Config = Default::default();
            config
                .set_num_nics_used(1)
                .set_rpc_threads(2)
                .set_init_dc_targets(12)
                .set_machine_id(0 as usize);

            assert!(start_instance(config.clone()).is_some());
        }
    }
}

pub fn end() {
    unsafe {
        crate::heap_descriptor::drop();
        crate::sh_service::drop();
        end_instance();
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
