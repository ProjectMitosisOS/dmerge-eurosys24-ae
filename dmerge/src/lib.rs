#![no_std]
#![feature(
core_intrinsics,
allocator_api,
nonnull_slice_from_raw_parts,
alloc_layout_extra,
get_mut_unchecked,
trait_alias,
)]
/// Distributed Merge: A set of os primitive for message passing.
extern crate alloc;

pub mod core_syscall_handler;
pub mod descriptors;
pub mod shadow_heap;
pub mod startup;
mod network;
pub use network::*;


mod rpc_service;
pub mod bindings;
/// Import MITOSIS
pub use mitosis;
pub use mitosis_macros;
pub use mitosis::KRdmaKit;
pub use mitosis::log;

use crate::mitosis_macros::declare_global;
pub use core_syscall_handler::DmergeSyscallHandler;


declare_global!(
    sh_service,
    crate::shadow_heap::ShadowHeapService
);

declare_global!(global_locks, alloc::vec::Vec<mitosis::linux_kernel_module::mutex::LinuxMutex<()>>);

#[inline]
pub unsafe fn get_shs_ref() -> &'static crate::shadow_heap::ShadowHeapService {
    crate::sh_service::get_ref()
}

#[inline]
pub unsafe fn get_shs_mut() -> &'static mut crate::shadow_heap::ShadowHeapService {
    crate::sh_service::get_mut()
}
