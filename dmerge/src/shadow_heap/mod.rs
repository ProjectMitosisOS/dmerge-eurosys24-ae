use alloc::vec::Vec;
use mitosis::descriptors::CompactPageTable;
use mitosis::kern_wrappers::task::Task;
use mitosis::KRdmaKit::rust_kernel_rdma_base::VmallocAllocator;
use mitosis::shadow_process::{COW4KPage, ShadowPageTable};
use mitosis::linux_kernel_module;

use crate::descriptors::heap::HeapDescriptor;
use crate::shadow_heap::vma::VMAPTGenerator;
use crate::log;
use vma::ShadowVMA;
use crate::descriptors::HeapMeta;

pub mod vma;

#[allow(dead_code)]
pub struct ShadowHeap {
    pub descriptor: HeapDescriptor,

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

        for vma in mm.get_vma_iter() {
            vma_descriptors.push(vma.generate_descriptor());
            shadow_vmas.push(ShadowVMA::new(vma, true));
            vma_page_table.push(Default::default());
        }

        for (idx, _) in mm.get_vma_iter().enumerate() {
            let pt: &mut CompactPageTable = vma_page_table.get_mut(idx).unwrap();
            let shadow_vma = shadow_vmas.get(idx).unwrap();
            VMAPTGenerator::new(shadow_vma,
                                &mut shadow_pt,
                                pt,
                                &heap_meta).generate();
        }
        mm.flush_tlb_mm();
        log::debug!("[ShadowHeap] Generate vma size {}",
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
            descriptor: HeapDescriptor {
                page_table: vma_page_table,
                vma: vma_descriptors,
                machine_info: rdma_meta,
                heap_meta: heap_meta,
            },
            shadow_page_table: Some(shadow_pt),
        }
    }

    // Apply the heap region into self (without local vma unmap)
    #[inline]
    pub fn apply_to(&mut self, file: *mut mitosis::bindings::file) {
        let mut task = Task::new();
        let des = &self.descriptor;

        (&des.vma).into_iter().enumerate().for_each(|(i, m)| {
            let vma = unsafe {
                task.map_one_region(file, &m, des.vma.get(i + 1))
            };
            if let Some(vma) = vma {
                // tune the bits
                let origin_vma_flags =
                    unsafe { mitosis::bindings::VMFlags::from_bits_unchecked(m.flags) };
                // crate::log::info!("orign vma: {:?}", origin_vma_flags);
                if origin_vma_flags.contains(mitosis::bindings::VMFlags::VM_ALLOC) {
                    // set the vma
                    mitosis::kern_wrappers::vma::VMA::new(vma).set_alloc();
                }
            } else {
                crate::log::debug!("not map success on vma (start 0x{:x}, sz {}) ",
                    m.get_start(), m.get_sz());
            }
        });
    }
}