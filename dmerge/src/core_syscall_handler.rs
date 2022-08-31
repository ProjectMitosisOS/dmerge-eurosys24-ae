use crate::descriptors::heap::HeapDescriptor;
use crate::KRdmaKit::rust_kernel_rdma_base::linux_kernel_module::c_types::*;
use crate::KRdmaKit::rust_kernel_rdma_base::linux_kernel_module::KernelResult;
use crate::shadow_heap::{HeapBundler, ShadowHeap};
use crate::descriptors::HeapMeta;
use mitosis::descriptors::RDMADescriptor;
use mitosis::remote_paging::AccessInfo;
use mitosis::syscalls::FileOperations;
use mitosis::os_network::bytes::ToBytes;
use mitosis::os_network::serialize::Serialize;
use mitosis::linux_kernel_module;

pub struct DmergeSyscallHandler {
    caller_status: Option<CallerData>,
    file: *mut mitosis::bindings::file,
}

impl Drop for DmergeSyscallHandler {
    fn drop(&mut self) {}
}

#[allow(dead_code)]
struct HeapDataStruct {
    id: usize,
    descriptor: crate::descriptors::heap::HeapDescriptor,
    access_info: mitosis::remote_paging::AccessInfo,
}

#[allow(dead_code)]
struct CallerData {
    // whether pin itself after close the fd
    ping_data: bool,
    heaps: Option<HeapDataStruct>,
}

#[allow(non_upper_case_globals)]
impl mitosis::syscalls::FileOperations for DmergeSyscallHandler {
    fn open(file: *mut mitosis::linux_kernel_module::bindings::file) -> KernelResult<Self> {
        unsafe {
            MY_VM_OP = Default::default();
            MY_VM_OP.open = Some(open_handler);
            MY_VM_OP.fault = Some(page_fault_handler);
            MY_VM_OP.access = None;
        }

        {
            let task = mitosis::kern_wrappers::task::Task::new();
            task.generate_mm();
        }

        Ok(Self {
            file: file as *mut _,
            caller_status: None,
        })
    }

    fn ioctrl(&mut self, cmd: c_uint, arg: c_ulong) -> c_long {
        match cmd {
            0 => self.syscall_register_heap(arg),
            1 => self.syscall_pull(arg),
            _ => {
                -1
            }
        }
    }

    fn mmap(&mut self, vma_p: *mut mitosis::linux_kernel_module::bindings::vm_area_struct) -> c_int {
        unsafe {
            (*vma_p).vm_private_data = (self as *mut Self).cast::<c_void>();
            (*vma_p).vm_ops = &mut MY_VM_OP as *mut crate::bindings::vm_operations_struct as *mut _;
        }
        0
    }
}

impl DmergeSyscallHandler {
    // ioctrl-0
    fn syscall_register_heap(&self, arg: c_ulong) -> c_long {
        mitosis::log::debug!("heap base addr: 0x{:x}", arg);

        let start_virt_addr = arg;

        let heap_service = unsafe { crate::get_shs_mut() };
        let hint = 73;
        heap_service.register_heap(hint as _, start_virt_addr as _);
        return 0;
    }
    // ioctrl-1
    fn syscall_pull(&self, _arg: c_ulong) -> c_long {
        let heap_service = unsafe { crate::get_shs_mut() };
        let hint = 73;


        // TODO: Introduce RPC to fetch the data
        if let Some((buf, sz)) = heap_service.query_descriptor_buf(hint as _) {
            if let Some(des) = HeapDescriptor::deserialize(buf.get_bytes()) {
                unsafe { crate::heap_descriptor::init(des) };
                {
                    let descriptor = unsafe { crate::get_heap_descriptor_mut() };
                    descriptor.apply_to(self.file);
                }
            }
        }
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
    let handler: *mut DmergeSyscallHandler = (*(*vmf).vma).vm_private_data as *mut _;
    (*handler).handle_page_fault(vmf)
}

impl DmergeSyscallHandler {
    #[inline(always)]
    unsafe fn handle_page_fault(&mut self, vmf: *mut crate::bindings::vm_fault) -> c_int {
        use mitosis::linux_kernel_module;
        let fault_addr = (*vmf).address;
        let descriptor = crate::get_heap_descriptor_mut();
        let new_page = if let Some(pa) = descriptor.lookup_pg_table(fault_addr) {
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

unsafe impl Sync for DmergeSyscallHandler {}

unsafe impl Send for DmergeSyscallHandler {}