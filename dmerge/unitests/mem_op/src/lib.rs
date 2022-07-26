#![no_std]

extern crate alloc;

use dmerge::{mitosis, log};

use mitosis::linux_kernel_module;

use krdma_test::*;

#[krdma_main]
fn kmain() {
    log::info!("in test dmerge memory operations");
}

#[krdma_drop]
fn clean() {
    // end_instance();
}
