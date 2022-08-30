use alloc::sync::Arc;
use alloc::vec::Vec;
use mitosis::descriptors::{CompactPageTable, ParentDescriptor};
use mitosis::kern_wrappers::task::Task;
use mitosis::KRdmaKit::rust_kernel_rdma_base::VmallocAllocator;
use mitosis::shadow_process::{COW4KPage, ShadowPageTable};
use mitosis::linux_kernel_module;
use mitosis::os_network::rdma::dc::DCTarget;

use crate::descriptors::heap::HeapDescriptor;
use crate::shadow_heap::vma::VMAPTGenerator;
use crate::log;
use super::ShadowVMA;
use crate::descriptors::HeapMeta;


#[allow(dead_code)]
pub struct ShadowHeap {
    pub descriptor: mitosis::descriptors::ParentDescriptor,

    shadow_vmas: Vec<ShadowVMA<'static>>,
    // Use copy currently
    shadow_page_table: core::option::Option<ShadowPageTable<COW4KPage>>,
}

impl ShadowHeap {
    pub fn new(rdma_meta: mitosis::descriptors::RDMADescriptor,
               heap_meta: HeapMeta) -> Self {
        let mut shadow_vmas: Vec<ShadowVMA<'static>> = Vec::new();
        let mut shadow_pt = ShadowPageTable::<mitosis::shadow_process::COW4KPage>::new();
        let mut vma_descriptors = Vec::new();
        let mut vma_page_table: Vec<CompactPageTable, VmallocAllocator> = Vec::new_in(VmallocAllocator);

        // local process task
        let task = crate::mitosis::kern_wrappers::task::Task::new();
        let mut mm = task.get_memory_descriptor();
        let heap_start = heap_meta.start_virt_addr;

        // Iter to every vma in the virt-addr space
        for vma in mm.get_vma_iter() {
            let vma_des = vma.generate_descriptor();
            // Filter for vma (if in range)
            if heap_start >= vma_des.get_start() && heap_start < vma_des.get_end() {
                vma_descriptors.push(vma_des);
                shadow_vmas.push(ShadowVMA::new(vma, true));
                vma_page_table.push(Default::default());
            }
        }

        for (idx, shadow_vma) in shadow_vmas.iter().enumerate() {
            let pt: &mut CompactPageTable = vma_page_table.get_mut(idx).unwrap();
            VMAPTGenerator::new(shadow_vma,
                                &mut shadow_pt,
                                pt,
                                &heap_meta).generate();
        }
        mm.flush_tlb_mm();
        log::debug!("[ShadowHeap] Generate vma size: {}",
            shadow_vmas.len());
        for i in 0..vma_descriptors.len() {
            let des = &vma_descriptors[i];
            log::debug!("vma {} addr space[0x{:x} ~ 0x{:x}] len({}) with flag {:b}. is_anonymous:{}",
                i,
                des.get_start(), des.get_end(), des.get_sz(),
                des.get_mmap_flags(), des.is_anonymous())
        }
        // for item in 0..vma_page_table.len() {
        //     let table = &vma_page_table[item];
        //     log::debug!("item {} with length {}", item, table.table_len());
        // }

        Self {
            shadow_vmas,
            descriptor: mitosis::descriptors::ParentDescriptor {
                regs: task.generate_reg_descriptor(),
                page_table: vma_page_table,
                vma: vma_descriptors,
                machine_info: rdma_meta,
            },
            shadow_page_table: Some(shadow_pt),
        }
    }
}

impl ShadowHeap {
    pub fn get_descriptor_ref(&self) -> &ParentDescriptor {
        &self.descriptor
    }
}