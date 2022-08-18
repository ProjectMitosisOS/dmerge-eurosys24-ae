use mitosis::descriptors::{CompactPageTable, RDMADescriptor, RegDescriptor, VMADescriptor};
use crate::KRdmaKit::rust_kernel_rdma_base::VmallocAllocator;
use alloc::vec::Vec;
use mitosis::kern_wrappers::task::Task;
use crate::descriptors::HeapMeta;


/// HeapDescriptor
#[allow(dead_code)]
#[derive(Clone)]
pub struct HeapDescriptor {
    pub regs: RegDescriptor,
    pub page_table: Vec<CompactPageTable, VmallocAllocator>,
    pub vma: Vec<VMADescriptor>,
    pub machine_info: RDMADescriptor,
    pub heap_meta: HeapMeta,
}

impl Default for HeapDescriptor {
    fn default() -> Self {
        Self {
            regs: Default::default(),
            page_table: Vec::new_in(VmallocAllocator),
            vma: Vec::new(),
            machine_info: Default::default(),
            heap_meta: Default::default(),
        }
    }
}

impl HeapDescriptor {
    #[inline]
    pub fn apply_to(&mut self, file: *mut mitosis::bindings::file) {
        use mitosis::linux_kernel_module;

        let mut task = Task::new();
        let vma_len = self.vma.len();
        task.unmap_self();
        let offset = 1024 * 1024 * 1024 * 4 as u64;

        (&self.vma).into_iter().enumerate().for_each(|(i, m)| {
            // ensure only map into the heap space
            if self.page_table[i].table_len() > 0 && i == vma_len - 2 {
                let mapped_vma: VMADescriptor = VMADescriptor {
                    range: (m.get_start() - offset, m.get_end() - offset),
                    flags: m.flags,
                    prot: m.prot,
                    is_anonymous: m.is_anonymous,
                };
                crate::log::debug!("start to map vma start:0x{:x}, end:0x{:x}",
                    mapped_vma.get_start(), mapped_vma.get_end());
                let vma = unsafe {
                    task.map_one_region(file, &mapped_vma,
                                        self.vma.get(i + 1))
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
            }
        });

        task.set_mm_reg_states(&self.regs);
    }
}