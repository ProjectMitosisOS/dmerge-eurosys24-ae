use crate::linux_kernel_module::c_types::*;
use crate::linux_kernel_module::bindings::vm_area_struct;
use crate::*;

pub(crate) struct MySyscallHandler {
    file: *mut mitosis::bindings::file,
}


#[allow(non_upper_case_globals)]
impl FileOperations for MySyscallHandler {
    #[inline]
    fn open(
        _file: *mut crate::linux_kernel_module::bindings::file,
    ) -> crate::linux_kernel_module::KernelResult<Self> {
        Ok(Self {
            file: _file as *mut _
        })
    }

    #[allow(non_snake_case)]
    #[inline]
    fn ioctrl(&mut self, cmd: c_uint, arg: c_ulong) -> c_long {
        match cmd {
            0 => self.test_generate_heap_meta(arg),
            1 => self.test_self_vma_apply(arg),
            _ => {
                -1
            }
        }
    }

    #[inline]
    fn mmap(&mut self, _vma_p: *mut vm_area_struct) -> c_int {
        unimplemented!();
    }
}

impl MySyscallHandler {
    // ioctrl-0
    fn test_generate_heap_meta(&self, _arg: c_ulong) -> c_long {
        use dmerge::KRdmaKit::mem::Memory;

        let rdma_meta = mitosis::descriptors::RDMADescriptor::default();

        let mut mem = RMemPhy::new(1024);
        let heap_meta = HeapMeta {
            start_phy_addr: mem.get_dma_buf(),
            heap_size: mem.get_sz(),
        };
        let _meta = ShadowHeap::new(rdma_meta, heap_meta);

        0
    }
    // ioctrl-1
    fn test_self_vma_apply(&self, _arg: c_ulong) -> c_long {
        use dmerge::KRdmaKit::mem::Memory;

        let rdma_meta = mitosis::descriptors::RDMADescriptor::default();

        let mut mem = RMemPhy::new(1024);
        let heap_meta = HeapMeta {
            start_phy_addr: mem.get_dma_buf(),
            heap_size: mem.get_sz(),
        };
        let mut meta = ShadowHeap::new(rdma_meta, heap_meta);
        // meta.apply_to(self.file);
        0
    }
}


unsafe impl Sync for MySyscallHandler {}

unsafe impl Send for MySyscallHandler {}
