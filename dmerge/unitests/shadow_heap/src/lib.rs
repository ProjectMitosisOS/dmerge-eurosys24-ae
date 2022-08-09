#![no_std]

extern crate alloc;

use dmerge::{mitosis, log};

use mitosis::linux_kernel_module;

use krdma_test::*;
use crate::linux_kernel_module::println;
use hashbrown::{HashMap, HashSet};
use dmerge::shadow_heap::ShadowHeap;

fn test_generate_heap_meta() {
    let rdma_meta = mitosis::descriptors::RDMADescriptor::default();
    let meta = ShadowHeap::new(rdma_meta);


}

#[krdma_main]
fn kmain() {
    log::info!("in test shadow heap");

    test_generate_heap_meta();
}


#[krdma_drop]
fn clean() {
    log::info!("drop instance");
    // end_instance();
}
