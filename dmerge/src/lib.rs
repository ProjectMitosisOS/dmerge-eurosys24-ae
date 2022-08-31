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
/// Import MITOSIS
pub use mitosis;
pub use mitosis_macros;
pub use mitosis::KRdmaKit;
pub use mitosis::log;
pub use mitosis::bindings;
use mitosis::startup::{end_instance, start_instance};


use crate::mitosis_macros::declare_global;
pub use core_syscall_handler::DmergeSyscallHandler;


declare_global!(heap_descriptor, crate::descriptors::heap::HeapDescriptor);

declare_global!(
    sh_service,
    crate::shadow_heap::ShadowHeapService
);


#[inline]
pub unsafe fn get_heap_descriptor_ref() -> &'static crate::descriptors::heap::HeapDescriptor {
    crate::heap_descriptor::get_ref()
}

#[inline]
pub unsafe fn get_heap_descriptor_mut() -> &'static mut crate::descriptors::heap::HeapDescriptor {
    crate::heap_descriptor::get_mut()
}

#[inline]
pub unsafe fn get_shs_ref() -> &'static crate::shadow_heap::ShadowHeapService {
    crate::sh_service::get_ref()
}

#[inline]
pub unsafe fn get_shs_mut() -> &'static mut crate::shadow_heap::ShadowHeapService {
    crate::sh_service::get_mut()
}

pub fn start_dmerge() {
    unsafe {
        crate::heap_descriptor::init(Default::default());
        crate::sh_service::init(Default::default());

        // mitosis
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

pub fn end_dmerge() {
    unsafe {
        crate::heap_descriptor::drop();
        crate::sh_service::drop();
        end_instance();
    };
}