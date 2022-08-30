use mitosis::shadow_process::{Copy4KPage, ShadowPageTable};
use mitosis::kern_wrappers::vma_iters::VMWalkEngine;
use mitosis::kern_wrappers::mm::{PhyAddrType, VirtAddrType};
use mitosis::kern_wrappers::vma::VMA;
use mitosis::bindings::*;
use crate::descriptors::HeapMeta;


type COWPageTable = mitosis::shadow_process::page_table::ShadowPageTable<mitosis::shadow_process::COW4KPage>;

pub struct ShadowVMA<'a> {
    vma_inner: VMA<'a>,
    shadow_file: *mut file,
    is_cow: bool,
}

impl<'a> ShadowVMA<'a> {
    pub fn new(vma: VMA<'a>, is_cow: bool) -> Self {
        // increment the file reference counter

        let file = unsafe { vma.get_file_ptr() };
        if !file.is_null() && is_cow {
            unsafe { pmem_get_file(file) };
        }

        // toggle the VM map flag
        Self {
            vma_inner: vma,
            is_cow: is_cow,
            shadow_file: file,
        }
    }

    pub fn backed_by_file(&self) -> bool {
        !self.shadow_file.is_null()
    }

    pub fn has_write_permission(&self) -> bool {
        self.vma_inner.get_flags().contains(VMFlags::WRITE)
            || self.vma_inner.get_flags().contains(VMFlags::MAY_WRITE)
    }
}

pub(crate) struct VMAPTGenerator<'a, 'b> {
    vma: &'a ShadowVMA<'a>,
    inner: &'b mut COWPageTable,
    inner_flat: &'b mut mitosis::descriptors::CompactPageTable,
    heap_meta: &'b HeapMeta,
}


impl<'a, 'b> VMAPTGenerator<'a, 'b> {
    pub fn new(
        vma: &'a ShadowVMA,
        inner: &'b mut COWPageTable,
        inner_flat: &'b mut mitosis::descriptors::CompactPageTable,
        heap_meta: &'b HeapMeta,
    ) -> Self {
        Self {
            vma,
            inner,
            inner_flat,
            heap_meta,
        }
    }
}

impl VMAPTGenerator<'_, '_> {
    /// Generate page table. Filter out these entries that are not in kernel heap range
    pub fn generate(&self) {
        let mut walk: mm_walk = Default::default();
        walk.pte_entry = Some(Self::handle_pte_entry);
        walk.private = self as *const _ as *mut mitosis::linux_kernel_module::c_types::c_void;

        let mut engine = VMWalkEngine::new(walk);
        unsafe { engine.walk(self.vma.vma_inner.get_raw_ptr()) };
    }

    #[allow(non_upper_case_globals)]
    #[allow(unused_variables)]
    pub unsafe extern "C" fn handle_pte_entry(
        pte: *mut pte_t,
        addr: mitosis::linux_kernel_module::c_types::c_ulong,
        _next: mitosis::linux_kernel_module::c_types::c_ulong,
        walk: *mut mm_walk,
    ) -> mitosis::linux_kernel_module::c_types::c_int {
        use core::intrinsics::{likely, unlikely};
        let my: &mut Self = &mut (*((*walk).private as *mut Self));

        let mut phy_addr = pmem_get_phy_from_pte(pte);
        if phy_addr > 0 {
            let start = my.vma.vma_inner.get_start();
            my.inner_flat
                .add_one((addr as VirtAddrType - start) as _, phy_addr as _);
        }
        0
    }

}
