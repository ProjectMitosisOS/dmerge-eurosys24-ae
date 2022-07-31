use alloc::vec::Vec;
use mitosis::descriptors::CompactPageTable;
use mitosis::KRdmaKit::rust_kernel_rdma_base::VmallocAllocator;
use mitosis::shadow_process::{Copy4KPage, ShadowPageTable, ShadowVMA};
use crate::descriptors::heap::HeapDescriptor;

#[allow(dead_code)]
pub struct ShadowHeap {
    descriptor: HeapDescriptor,

    shadow_vmas: Vec<ShadowVMA<'static>>,
    // Use copy currently
    shadow_page_table: core::option::Option<ShadowPageTable<Copy4KPage>>,
}

impl ShadowHeap {
    pub fn new(rdma_meta: mitosis::descriptors::RDMADescriptor) -> Self {
        let mut shadow_vmas: Vec<ShadowVMA<'static>> = Vec::new();
        let mut vma_descriptors = Vec::new();
        let mut vma_page_table: Vec<CompactPageTable, VmallocAllocator> = Vec::new_in(VmallocAllocator);

        Self {
            shadow_vmas,
            descriptor: HeapDescriptor {
                page_table: vma_page_table,
                vma: vma_descriptors,
                machine_info: rdma_meta,
            },
            shadow_page_table: None,
        }
    }
}