use alloc::string::String;
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
use mitosis::os_network::block_on;
use mitosis::os_network::timeout::TimeoutWRef;
use mitosis::rpc_service::HandlerConnectInfo;
use mitosis::startup::probe_remote_rpc_end;
use crate::remote_descriptor_fetch;
use crate::rpc_service::rpc_handlers::HeapDescriptorQueryReply;

const TIMEOUT_USEC: i64 = 1000_000; // 1s

pub struct DmergeSyscallHandler {
    caller_status: CallerData,
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

impl Default for CallerData {
    fn default() -> Self {
        Self {
            ping_data: false,
            heaps: None,
        }
    }
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
            caller_status: Default::default(),
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
    fn syscall_pull(&mut self, _arg: c_ulong) -> c_long {
        let heap_service = unsafe { crate::get_shs_mut() };
        let hint = 73;
        let handler_id = 73;
        let machine_id = 0;
        let cpu_id = mitosis::get_calling_cpu_id();

        // TODO: use as syscall
        {
            self.syscall_connect_session(machine_id,
                                         &String::from("fe80:0000:0000:0000:248a:0703:009c:7c94"),
                                         0);
        }
        // hold the lock on this CPU TODO: add function in MITOSIS
        // unsafe { mitosis::global_locks::get_ref()[cpu_id].lock() };

        let caller = unsafe {
            mitosis::rpc_caller_pool::CallerPool::get_global_caller(cpu_id)
                .expect("the caller should be properly initialized")
        };

        let remote_session_id = unsafe {
            mitosis::startup::calculate_session_id(
                machine_id as _,
                cpu_id,
                mitosis::get_max_caller_num(),
            )
        };

        let my_session_id = unsafe {
            mitosis::startup::calculate_session_id(
                mitosis::get_mac_id(),
                cpu_id,
                mitosis::get_max_caller_num(),
            )
        };

        let res = caller.sync_call::<usize>(
            remote_session_id,
            my_session_id,
            mitosis::rpc_handlers::RPCId::Query as _,
            handler_id as _,
        );

        if res.is_err() {
            crate::log::error!("failed to call {:?}", res);
            crate::log::info!(
                "sanity check pending reqs {:?}",
                caller.get_pending_reqs(remote_session_id)
            );
            // unsafe { mitosis::global_locks::get_ref()[cpu_id].unlock() };
            return -1;
        };

        let mut timeout_caller = TimeoutWRef::new(
            caller, 10 * TIMEOUT_USEC);

        use mitosis::os_network::serialize::Serialize;

        let _reply = match block_on(&mut timeout_caller) {
            Ok((msg, reply)) => {
                caller.register_recv_buf(msg)
                    .expect("register msg buffer cannot fail");
                match HeapDescriptorQueryReply::deserialize(&reply) {
                    Some(d) => {
                        crate::log::debug!("sanity check query descriptor result {:?}", d);
                        if !d.ready {
                            crate::log::error!("failed to lookup handler id: {:?}", handler_id);
                            return -1;
                        }
                        let desc_buf = remote_descriptor_fetch(d, caller, remote_session_id);

                        crate::log::debug!("sanity check fetched desc_buf {:?}", desc_buf.is_ok());
                        if desc_buf.is_err() {
                            crate::log::error!("failed to fetch descriptor {:?}", desc_buf.err());
                            return -1;
                        }
                        let des = HeapDescriptor::deserialize(desc_buf.unwrap().get_bytes());
                        if des.is_none() {
                            crate::log::error!("failed to deserialize the heap descriptor");
                            return -1;
                        }
                        let mut des = des.unwrap();

                        let access_info = AccessInfo::new(&des.machine_info);
                        if access_info.is_none() {
                            crate::log::error!("failed to create access info");
                            return -1;
                        }
                        des.apply_to(self.file);
                        self.caller_status.heaps = Some(HeapDataStruct {
                            id: handler_id as _,
                            descriptor: des,
                            access_info: access_info.unwrap(),
                        });
                        return 0;
                    }

                    None => {
                        crate::log::error!("Deserialize error");
                        return -1;
                    }
                }
                return 0;
            }
            Err(e) => {
                crate::log::error!("client receiver reply err {:?}", e);
                // unsafe { mitosis::global_locks::get_ref()[cpu_id].unlock() };
                return -1;
            }
        };
    }


    #[inline]
    fn syscall_connect_session(
        &mut self,
        machine_id: usize,
        gid: &alloc::string::String,
        nic_idx: usize,
    ) -> c_long {
        crate::log::debug!("connect remote machine id: {}", machine_id);
        let info = HandlerConnectInfo::create(gid, nic_idx as _, nic_idx as _);
        match probe_remote_rpc_end(machine_id, info) {
            Some(_) => {
                crate::log::debug!("connect to nic {}@{} success", nic_idx, gid);
                0
            }
            _ => {
                crate::log::error!("failed to connect {}@{} success", nic_idx, gid);
                -1
            }
        }
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
        let heap = self.caller_status.heaps.as_mut().unwrap();

        let new_page = if let Some(pa) =
        heap.descriptor.lookup_pg_table(fault_addr) {
            let access_info = AccessInfo::new(&heap.descriptor.machine_info);
            if access_info.is_none() {
                crate::log::error!("failed to create access info");
                None
            } else {
                heap.descriptor.read_remote_page(fault_addr,
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