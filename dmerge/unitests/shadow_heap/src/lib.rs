#![no_std]

extern crate alloc;

use dmerge::{mitosis, log};

use mitosis::linux_kernel_module;
use crate::mitosis::syscalls::SysCallsService;

#[allow(dead_code)]
struct Module {
    service: SysCallsService<dmerge::DmergeSyscallHandler>,
}

impl linux_kernel_module::KernelModule for Module {
    fn init() -> linux_kernel_module::KernelResult<Self> {
        dmerge::start_dmerge();

        Ok(Self {
            service: SysCallsService::<dmerge::DmergeSyscallHandler>::new()?,
        })
    }
}

impl Drop for Module {
    fn drop(&mut self) {
        dmerge::end_dmerge();
        log::info!("drop system call modules");
    }
}

linux_kernel_module::kernel_module!(
    Module,
    author: b"lfm",
    description: b"A kernel module for testing system calls",
    license: b"GPL"
);
