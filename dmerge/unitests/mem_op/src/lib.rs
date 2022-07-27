#![no_std]

extern crate alloc;

use dmerge::{mitosis, log};

use mitosis::linux_kernel_module;

use krdma_test::*;
use crate::linux_kernel_module::println;
use hashbrown::{HashMap, HashSet};

type KObject = (u64, usize);

struct ObjectHeap {
    kv: HashMap<u32, KObject>,
}

impl ObjectHeap {
    pub fn put(&mut self, key: u32, addr: u64, sz: usize) {
        self.kv.insert(key, (addr, sz));
    }

    pub fn get(&self, key: u32) -> Option<&KObject> {
        self.kv.get(&key)
    }
}

struct TestMem {
    objectHeap: ObjectHeap,
}

impl TestMem {
    pub fn mem_push(&mut self) {}

    pub fn mem_merge(&mut self) {}
}

#[krdma_main]
fn kmain() {
    log::info!("in test dmerge memory operations");
}


#[krdma_drop]
fn clean() {
    log::info!("drop instance");
    // end_instance();
}
