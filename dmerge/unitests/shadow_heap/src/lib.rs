#![no_std]

extern crate alloc;

use dmerge::{mitosis, log};

use mitosis::linux_kernel_module;
use dmerge::mitosis::Config;
use crate::mitosis::syscalls::SysCallsService;

#[allow(dead_code)]
struct Module {
    service: SysCallsService<dmerge::DmergeSyscallHandler>,
}

impl linux_kernel_module::KernelModule for Module {
    fn init() -> linux_kernel_module::KernelResult<Self> {
        let mut config: Config = Default::default();
        config
            .set_num_nics_used(1)
            .set_rpc_threads(2)
            .set_init_dc_targets(12)
            .set_machine_id(0 as usize);
        dmerge::startup::start_dmerge(&config);

        Ok(Self {
            service: SysCallsService::<dmerge::DmergeSyscallHandler>::new()?,
        })
    }
}

impl Drop for Module {
    fn drop(&mut self) {
        dmerge::startup::end_dmerge();
        log::info!("drop system call modules");
    }
}

linux_kernel_module::kernel_module!(
    Module,
    author: b"lfm",
    description: b"A kernel module for testing system calls",
    license: b"GPL"
);
