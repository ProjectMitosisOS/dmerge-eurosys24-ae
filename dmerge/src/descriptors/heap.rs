use mitosis::descriptors::{CompactPageTable, RDMADescriptor, VMADescriptor};
use crate::KRdmaKit::rust_kernel_rdma_base::VmallocAllocator;
use alloc::vec::Vec;
use crate::descriptors::HeapMeta;


/// HeapDescriptor
#[allow(dead_code)]
#[derive(Clone)]
pub struct HeapDescriptor {
    pub page_table: Vec<CompactPageTable, VmallocAllocator>,
    pub vma: Vec<VMADescriptor>,
    pub machine_info: RDMADescriptor,
    pub heap_meta: HeapMeta,
}

impl Default for HeapDescriptor {
    fn default() -> Self {
        Self {
            page_table: Vec::new_in(VmallocAllocator),
            vma: Vec::new(),
            machine_info: Default::default(),
            heap_meta: Default::default(),
        }
    }
}