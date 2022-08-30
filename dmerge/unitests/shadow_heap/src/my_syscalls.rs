use x86_64::PhysAddr;
use dmerge::descriptors::heap::HeapDescriptor;
use crate::linux_kernel_module::c_types::*;
use crate::linux_kernel_module::bindings::vm_area_struct;
use crate::*;
use dmerge::mitosis::os_network::bytes::ToBytes;
use dmerge::mitosis::os_network::serialize::Serialize;
use dmerge::mitosis::remote_paging::AccessInfo;
use dmerge::shadow_heap::HeapBundler;
use crate::mitosis::descriptors::RDMADescriptor;

pub(crate) struct MySyscallHandler {
    file: *mut mitosis::bindings::file,
}

impl Drop for MySyscallHandler {
    fn drop(&mut self) {}
}


#[allow(non_upper_case_globals)]
impl FileOperations for MySyscallHandler {
    #[inline]
    fn open(
        file: *mut crate::linux_kernel_module::bindings::file,
    ) -> crate::linux_kernel_module::KernelResult<Self> {
        unsafe {
            MY_VM_OP = Default::default();
            MY_VM_OP.open = Some(open_handler);
            MY_VM_OP.fault = Some(page_fault_handler);
            MY_VM_OP.access = None;
        };

        {
            let task = mitosis::kern_wrappers::task::Task::new();
            task.generate_mm();
        }

        Ok(Self {
            file: file as *mut _
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
    fn mmap(&mut self, vma_p: *mut vm_area_struct) -> c_int {
        unsafe {
            (*vma_p).vm_private_data = (self as *mut Self).cast::<c_void>();
            (*vma_p).vm_ops = &mut MY_VM_OP as *mut crate::bindings::vm_operations_struct as *mut _;
        }
        0
    }
}


impl MySyscallHandler {
    // ioctrl-0
    fn test_generate_heap_meta(&self, arg: c_ulong) -> c_long {
        use dmerge::KRdmaKit::mem::Memory;
        log::debug!("heap base addr: 0x{:x}", arg);
        let rdma_meta = mitosis::descriptors::RDMADescriptor::default();

        let start_virt_addr = arg;
        let res = RDMADescriptor::new_from_dc_target_pool();
        if res.is_none() {
            return -1;
        }
        let tmp = res.unwrap();

        let (target, descriptor) = RDMADescriptor::new_from_dc_target_pool().unwrap();

        // create bundler
        let bundler = HeapBundler::new(
            ShadowHeap::new(descriptor, HeapMeta {
                start_virt_addr,
            }),
            target,
        );
        let mut buf = unsafe { mitosis::get_mem_pool_mut() }.pop_one();

        // TODO: move into ShadowHeap::new
        {
            let parent_des = &bundler.heap.descriptor.clone();
            parent_des.serialize(buf.get_bytes_mut());
        }

        if let Some(mut des) = HeapDescriptor::deserialize(buf.get_bytes()) {
            unsafe { crate::heap_descriptor::init(des) };
        }

        let heap_service = unsafe { crate::get_shs_mut() };
        heap_service.add_bundler(73 as _, bundler);


        return 0;
    }
    // ioctrl-1
    fn test_self_vma_apply(&self, _arg: c_ulong) -> c_long {
        // read from global
        let mut descriptor = unsafe { crate::get_heap_descriptor_mut() };
        descriptor.apply_to(self.file);
        0
    }
}

/// The fault handler parts
static mut MY_VM_OP: crate::bindings::vm_operations_struct = unsafe {
    core::mem::transmute([0u8; core::mem::size_of::<crate::bindings::vm_operations_struct>()])
};

#[allow(dead_code)]
unsafe extern "C" fn open_handler(_area: *mut crate::bindings::vm_area_struct) {}


#[allow(dead_code)]
unsafe extern "C" fn page_fault_handler(vmf: *mut crate::bindings::vm_fault) -> c_int {
    let handler: *mut MySyscallHandler = (*(*vmf).vma).vm_private_data as *mut _;
    (*handler).handle_page_fault(vmf)
}

impl MySyscallHandler {
    #[inline(always)]
    unsafe fn handle_page_fault(&mut self, vmf: *mut crate::bindings::vm_fault) -> c_int {
        let fault_addr = (*vmf).address;
        let mut descriptor = unsafe { crate::get_heap_descriptor_mut() };
        let new_page = if let Some(pa) = descriptor.lookup_pg_table(fault_addr) {
            crate::log::debug!("find page fault res. va: 0x{:x}, pa: 0x{:x}", fault_addr,pa);
            let access_info = AccessInfo::new(&descriptor.machine_info);
            if access_info.is_none() {
                crate::log::error!("failed to create access info");
                None
            } else {
                descriptor.read_remote_page(fault_addr,
                                            access_info.as_ref().unwrap())
            }
        } else {
            None
        };

        match new_page {
            Some(new_page_p) => {
                (*vmf).page = new_page_p as *mut _;
                0
            }
            None => {
                crate::log::debug!(
                    "[handle_page_fault] Failed to read the remote page, fault addr: 0x{:x}",
                    fault_addr
                );
                crate::bindings::FaultFlags::SIGSEGV.bits() as linux_kernel_module::c_types::c_int
            }
        }
    }
}

unsafe impl Sync for MySyscallHandler {}

unsafe impl Send for MySyscallHandler {}
