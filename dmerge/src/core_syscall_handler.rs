use alloc::string::String;
use alloc::vec::Vec;
use core::intrinsics::size_of;
use core::mem::size_of_val;
use hashbrown::HashSet;
use mitosis::kern_wrappers::mm::VirtAddrType;
use crate::descriptors::heap::HeapDescriptor;
use crate::KRdmaKit::rust_kernel_rdma_base::linux_kernel_module::c_types::*;
use crate::KRdmaKit::rust_kernel_rdma_base::linux_kernel_module::KernelResult;
use mitosis::remote_paging::AccessInfo;
use mitosis::os_network::bytes::ToBytes;
use mitosis::linux_kernel_module;
use mitosis::linux_kernel_module::file_operations::{File, SeekFrom};
use mitosis::linux_kernel_module::println;
use mitosis::linux_kernel_module::user_ptr::{UserSlicePtrReader, UserSlicePtrWriter};
use mitosis::os_network::block_on;
use mitosis::os_network::timeout::TimeoutWRef;
use mitosis::rpc_service::HandlerConnectInfo;
use mitosis::startup::probe_remote_rpc_end;
use crate::KRdmaKit::net_util::gid_to_str;
use crate::KRdmaKit::rust_kernel_rdma_base::linux_kernel_module::file_operations::{ReadFn, SeekFn, WriteFn};
use crate::remote_descriptor_fetch;
use crate::rpc_service::rpc_handlers::{HeapDescriptorQueryReply, RegisterRemoteReply, RegisterRemoteReq};

const TIMEOUT_USEC: i64 = 1000_000; // 1s

pub struct DmergeSyscallHandler {
    caller_status: CallerData,
    file: *mut mitosis::bindings::file,
}

impl Drop for DmergeSyscallHandler {
    fn drop(&mut self) {
        if let Some(hint) = self.caller_status.private_heap_hint {
            let heap_service = unsafe { crate::get_shs_mut() };
            heap_service.unregister(hint as _);
        }
    }
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
    // TODO: Now one process only support register one unique private heap
    private_heap_hint: Option<u64>,
    public_heaps: Vec<HeapDataStruct>,
}

impl Default for CallerData {
    fn default() -> Self {
        Self {
            ping_data: false,
            private_heap_hint: None,
            public_heaps: Vec::new(),
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

        #[cfg(feature = "process")]
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
            0 => {
                /* register heap */
                use crate::bindings::register_req_t;
                use crate::mitosis::linux_kernel_module::bindings::_copy_from_user;
                let mut req: register_req_t = Default::default();
                unsafe {
                    _copy_from_user(
                        (&mut req as *mut register_req_t).cast::<c_void>(),
                        arg as *mut c_void,
                        core::mem::size_of_val(&req) as u64,
                    )
                };

                if let Some(hint) = self.caller_status.private_heap_hint {
                    hint as _
                } else {
                    let heap_hint = unsafe { crate::get_heap_id_generator_mut().alloc_one_id() };
                    let _ = self.syscall_register_mem(req.heap_base as _, heap_hint as _);
                    self.caller_status.private_heap_hint = Some(heap_hint);
                    heap_hint as _
                }
            }
            1 => {
                /* pull */
                use crate::bindings::pull_req_t;
                use crate::mitosis::linux_kernel_module::bindings::_copy_from_user;
                let mut req: pull_req_t = Default::default();
                unsafe {
                    _copy_from_user(
                        (&mut req as *mut pull_req_t).cast::<c_void>(),
                        arg as *mut c_void,
                        core::mem::size_of_val(&req) as u64,
                    )
                };
                self.syscall_rmap(req.heap_hint as _,
                                  req.machine_id as _,
                                  req.eager_fetch)
            }
            3 => {
                /* connect */
                use crate::bindings::connect_req_t;
                use crate::mitosis::linux_kernel_module::bindings::_copy_from_user;
                let mut req: connect_req_t = Default::default();
                unsafe {
                    _copy_from_user(
                        (&mut req as *mut connect_req_t).cast::<c_void>(),
                        arg as *mut c_void,
                        core::mem::size_of_val(&req) as u64,
                    )
                };

                let mut addr_buf: [u8; 39] = [0; 39];
                let addr = {
                    unsafe {
                        _copy_from_user(
                            addr_buf.as_mut_ptr().cast::<c_void>(),
                            req.gid as *mut c_void,
                            39,
                        )
                    };
                    // now get addr of GID format
                    core::str::from_utf8(&addr_buf).unwrap()
                };
                let (machine_id, gid, nic_id) = (req.machine_id, String::from(addr), req.nic_id);
                self.syscall_connect_session(machine_id as _,
                                             &gid,
                                             nic_id as _)
            }

            4 => {
                /* Get gid and machine id */
                use crate::bindings::get_mac_id_req_t;
                use crate::mitosis::linux_kernel_module::bindings::{_copy_from_user, _copy_to_user};
                let mut req: get_mac_id_req_t = Default::default();
                unsafe {
                    _copy_from_user(
                        (&mut req as *mut get_mac_id_req_t).cast::<c_void>(),
                        arg as *mut c_void,
                        core::mem::size_of_val(&req) as u64,
                    )
                };
                let nic_idx = req.nic_idx;
                let ctx = unsafe { mitosis::get_rdma_context_ref(nic_idx as _) };
                if ctx.is_some() {
                    let gid_str = gid_to_str(ctx.unwrap().get_gid());
                    let machine_id = unsafe { mitosis::get_mac_id() as usize };
                    // format_mac_address(gid_str.as_str());
                    unsafe {
                        _copy_to_user(
                            req.gid as _,
                            gid_str.as_ptr().cast::<c_void>(),
                            gid_str.len() as _,
                        );

                        _copy_to_user(
                            (req.machine_id as *mut _) as _,
                            (&machine_id as *const usize).cast::<c_void>(),
                            size_of_val(&machine_id) as _,
                        );
                    };
                    gid_str.len() as _
                } else {
                    crate::log::error!("[get_mac_id] not found at nic idx: {}", nic_idx);
                    0
                }
            }
            5 => {
                /* Register to remote heap */
                use crate::bindings::register_remote_req_t;
                use crate::mitosis::linux_kernel_module::bindings::_copy_from_user;
                let mut req: register_remote_req_t = Default::default();
                unsafe {
                    _copy_from_user(
                        (&mut req as *mut register_remote_req_t).cast::<c_void>(),
                        arg as *mut c_void,
                        core::mem::size_of_val(&req) as u64,
                    )
                };
                // return the remote heap hint ID
                let tmp_hint = unsafe { crate::get_heap_id_generator_mut().alloc_one_id() };
                let hint = self.syscall_register_remote_heap(
                    req.heap_base as _,
                    tmp_hint as _,
                    req.machine_id as _);
                hint as _
            }
            _ => {
                -1
            }
        }
    }

    fn mmap(&mut self, vma_p: *mut mitosis::linux_kernel_module::bindings::vm_area_struct) -> c_int {
        unsafe {
            (*vma_p).vm_private_data = (self as *mut Self).cast::<c_void>();
            (*vma_p).vm_ops = &mut MY_VM_OP as *mut mitosis::bindings::vm_operations_struct as *mut _;
        }
        0
    }

    const READ: ReadFn<Self> = Some(Self::read_fn);
    const WRITE: WriteFn<Self> = Some(Self::write_fn);
    const SEEK: SeekFn<Self> = Some(Self::seek_fn);
}

impl DmergeSyscallHandler {
    fn read_fn(_self: &DmergeSyscallHandler, _file: &File, _writer: &mut UserSlicePtrWriter, _len: u64) -> KernelResult<()> {
        Ok(())
    }

    fn write_fn(_self: &DmergeSyscallHandler, _writer: &mut UserSlicePtrReader, _len: u64) -> KernelResult<()> {
        Ok(())
    }

    fn seek_fn(_self: &DmergeSyscallHandler, _file: &File, _seek_from: SeekFrom) -> KernelResult<u64> {
        Ok(0)
    }
}

impl DmergeSyscallHandler {
    // ioctrl-0
    fn syscall_register_mem(&self, start_virt_addr: u64, hint: usize) -> c_long {
        let heap_service = unsafe { crate::get_shs_mut() };
        let _ = heap_service.register_heap(hint as _, start_virt_addr as _);
        return 0;
    }


    // ioctrl-1
    fn syscall_rmap(&mut self, hander_id: usize, machine_id: usize, eager_fetch: bool) -> c_long {
        let (handler_id, machine_id) = (hander_id, machine_id);
        let cpu_id = mitosis::get_calling_cpu_id();

        // hold the lock on this CPU
        unsafe { crate::global_locks::get_ref()[cpu_id].lock() };

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
            crate::rpc_service::rpc_handlers::RPCId::Query as _,
            handler_id as _,
        );

        if res.is_err() {
            crate::log::error!("failed to call {:?}", res);
            crate::log::info!(
                "sanity check pending reqs {:?}",
                caller.get_pending_reqs(remote_session_id)
            );
            unsafe { crate::global_locks::get_ref()[cpu_id].unlock() };
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
                            unsafe { crate::global_locks::get_ref()[cpu_id].unlock() };
                            return -1;
                        }
                        let desc_buf = remote_descriptor_fetch(
                            d.sz,
                            d.pa,
                            caller,
                            remote_session_id);

                        crate::log::debug!("sanity check fetched desc_buf {:?}", desc_buf.is_ok());
                        if desc_buf.is_err() {
                            crate::log::error!("failed to fetch descriptor {:?}", desc_buf.err());
                            unsafe { crate::global_locks::get_ref()[cpu_id].unlock() };
                            return -1;
                        }
                        let des = HeapDescriptor::deserialize(desc_buf.unwrap().get_bytes());
                        if des.is_none() {
                            crate::log::error!("failed to deserialize the heap descriptor");
                            unsafe { crate::global_locks::get_ref()[cpu_id].unlock() };
                            return -1;
                        }
                        let mut des = des.unwrap();

                        let access_info = AccessInfo::new(&des.machine_info);
                        if access_info.is_none() {
                            crate::log::error!("failed to create access info");
                            unsafe { crate::global_locks::get_ref()[cpu_id].unlock() };
                            return -1;
                        }

                        des.apply_to(self.file, eager_fetch);
                        self.caller_status.public_heaps.push(HeapDataStruct {
                            id: handler_id as _,
                            descriptor: des,
                            access_info: access_info.unwrap(),
                        });
                        unsafe { crate::global_locks::get_ref()[cpu_id].unlock() };
                        return 0;
                    }

                    None => {
                        crate::log::error!("Deserialize `HeapDescriptorQueryReply` error");
                        unsafe { crate::global_locks::get_ref()[cpu_id].unlock() };
                        return -1;
                    }
                }
            }
            Err(e) => {
                crate::log::error!("client receiver reply err {:?}", e);
                unsafe { crate::global_locks::get_ref()[cpu_id].unlock() };
                return -1;
            }
        };
    }


    // ioctrl-3
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

impl DmergeSyscallHandler {
    // ioctrl-5
    fn syscall_register_remote_heap(&self, start_virt_addr: u64,
                                    local_hint: usize,
                                    remote_machine_id: usize) -> c_long {
        let heap_service = unsafe { crate::get_shs_mut() };
        let machine_id = remote_machine_id;
        // Step1: `Local push`
        let _ = heap_service.register_heap(local_hint as _, start_virt_addr as _);
        // Step2: `Remote pull` and `remote pull`. Implemented by RPC and one-sided READ
        let des_buf = heap_service.query_descriptor_buf(local_hint as _);
        let register_remote_req: Option<RegisterRemoteReq> = match des_buf {
            Some((addr, len)) => {
                Some(RegisterRemoteReq {
                    pa: addr.get_pa(),
                    sz: len,
                    source_machine_id: unsafe { mitosis::get_mac_id() },
                    ready: true,
                })
            }
            _ => { None }
        };
        if register_remote_req.is_none() {
            crate::log::error!("failed to register local heap");
            return -1;
        }
        // Start RPC.
        let cpu_id = mitosis::get_calling_cpu_id();
        unsafe { crate::global_locks::get_ref()[cpu_id].lock() };
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

        let res = caller.sync_call::<RegisterRemoteReq>(
            remote_session_id,
            my_session_id,
            crate::rpc_service::rpc_handlers::RPCId::RemoteRegister as _,
            register_remote_req.unwrap() as _,
        );

        if res.is_err() {
            crate::log::error!("failed to call {:?}", res);
            crate::log::info!(
                "sanity check pending reqs {:?}",
                caller.get_pending_reqs(remote_session_id)
            );
            unsafe { crate::global_locks::get_ref()[cpu_id].unlock() };
            return -1;
        };
        let mut timeout_caller = TimeoutWRef::new(
            caller, 10 * TIMEOUT_USEC);

        use mitosis::os_network::serialize::Serialize;
        let mut res_hint = -1;
        let _reply = match block_on(&mut timeout_caller) {
            Ok((msg, reply)) => {
                caller.register_recv_buf(msg)
                    .expect("register msg buffer cannot fail");
                match RegisterRemoteReply::deserialize(&reply) {
                    Some(register_remote_reply) => {
                        res_hint = register_remote_reply.heap_hint as isize;
                        unsafe { crate::global_locks::get_ref()[cpu_id].unlock() };
                    }
                    None => {
                        crate::log::error!("Deserialize `RegisterRemoteReply` error");
                        unsafe { crate::global_locks::get_ref()[cpu_id].unlock() };
                        return -1;
                    }
                }
            }
            Err(e) => {
                crate::log::error!("client receiver reply err {:?}", e);
                unsafe { crate::global_locks::get_ref()[cpu_id].unlock() };
                return -1;
            }
        };
        // End RPC
        // Step3: Return back to user. Wait for consumer's `pull`
        // And we can directly free the local heap
        heap_service.unregister(local_hint as _);
        return res_hint as _;
    }
}

/// The fault handler parts
static mut MY_VM_OP: mitosis::bindings::vm_operations_struct = unsafe {
    core::mem::transmute([0u8; core::mem::size_of::<mitosis::bindings::vm_operations_struct>()])
};

#[allow(dead_code)]
unsafe extern "C" fn open_handler(_area: *mut mitosis::bindings::vm_area_struct) {}


#[allow(dead_code)]
unsafe extern "C" fn page_fault_handler(vmf: *mut mitosis::bindings::vm_fault) -> c_int {
    let handler: *mut DmergeSyscallHandler = (*(*vmf).vma).vm_private_data as *mut _;
    (*handler).handle_page_fault(vmf)
}

impl DmergeSyscallHandler {
    #[inline(always)]
    unsafe fn handle_page_fault(&mut self, vmf: *mut mitosis::bindings::vm_fault) -> c_int {
        let fault_addr = (*vmf).address;
        let heaps = &mut self.caller_status.public_heaps;
        crate::log::debug!("in page fault. heap len {}", heaps.len());
        let mut new_page: Option<*mut mitosis::bindings::page> = None;
        for heap in heaps {
            let cur_page = if let Some(_pa) =
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
            if cur_page.is_some() {
                new_page = cur_page;
                break;
            }
        }
        if new_page.is_none() {
            crate::log::error!("Can not find page for fault_addr 0x{:x}", fault_addr);
        }


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
                mitosis::bindings::FaultFlags::SIGSEGV.bits() as linux_kernel_module::c_types::c_int
            }
        }
    }
}

unsafe impl Sync for DmergeSyscallHandler {}

unsafe impl Send for DmergeSyscallHandler {}