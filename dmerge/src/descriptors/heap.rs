use mitosis::descriptors::{CompactPageTable, RDMADescriptor, VMADescriptor};
use crate::KRdmaKit::rust_kernel_rdma_base::VmallocAllocator;
use alloc::vec::Vec;


/// HeapDescriptor
#[allow(dead_code)]
#[derive(Clone)]
pub struct HeapDescriptor {
    pub page_table: Vec<CompactPageTable, VmallocAllocator>,
    pub vma: Vec<VMADescriptor>,
    pub machine_info: RDMADescriptor,
}

impl Default for HeapDescriptor {
    fn default() -> Self {
        Self {
            page_table: Vec::new_in(VmallocAllocator),
            vma: Vec::new(),
            machine_info: Default::default(),
        }
    }
}