use alloc::boxed::Box;
use mitosis::os_network::msg::UDMsg;
use mitosis::os_network::ud::{UDDatagram, UDFactory};
use mitosis::os_network::ud_receiver::{UDReceiver, UDReceiverFactory};
use mitosis::os_network::Future;
use mitosis::os_network::Factory;
use mitosis::os_network::future::Async;
use mitosis::rpc_service::Service;
use mitosis::linux_kernel_module::c_types::*;
use mitosis::linux_kernel_module;
use rust_kernel_linux_util::kthread;
use rust_kernel_linux_util::timer::KTimer;
use core::sync::atomic::{AtomicUsize, Ordering};

static RPC_HANDLER_READY_NUM: AtomicUsize = AtomicUsize::new(0);
const YIELD_THRESHOLD: usize = 10000;
const YIELD_TIME_USEC: i64 = 2000;

// 1ms
pub(crate) fn wait_handlers_ready_barrier(wait_num: usize) {
    loop {
        if RPC_HANDLER_READY_NUM.load(Ordering::SeqCst) >= wait_num {
            return;
        }
    }
}

struct ThreadCTX {
    pub(crate) id: usize,
    pub(crate) nic_to_use: usize,
}

#[allow(non_snake_case)]
pub(crate) extern "C" fn worker(ctx: *mut c_void) -> c_int {
    let arg = unsafe { Box::from_raw(ctx as *mut ThreadCTX) };

    // init the UD RPC hook
    type UDRPCHook<'a, 'b> =
    mitosis::os_network::rpc::hook::RPCHook<'a, 'b,
        UDDatagram<'a>, UDReceiver<'a>, UDFactory<'a>>;

    let local_context = unsafe { mitosis::get_rdma_context_ref(arg.nic_to_use).unwrap() };
    let lkey = unsafe { local_context.get_lkey() };

    crate::log::info!(
            "DMERGE RPC thread {} started, listing on gid: {}",
            arg.id,
            local_context.get_gid_as_string()
        );

    let server_ud = unsafe {
        mitosis::get_ud_factory_ref(arg.nic_to_use)
            .expect("failed to query the factory")
            .create(())
            .expect("failed to create server UD")
    };
    let temp_ud = server_ud.clone();

    unsafe {
        mitosis::get_rdma_cm_server_ref(arg.nic_to_use)
            .unwrap()
            .reg_ud(Service::calculate_qd_hint(arg.id), server_ud.get_qp())
    };

    let mut rpc_server = UDRPCHook::new(
        unsafe { mitosis::get_ud_factory_ref(arg.nic_to_use).unwrap() },
        server_ud,
        UDReceiverFactory::new()
            .set_qd_hint(Service::calculate_qd_hint(arg.id) as _)
            .set_lkey(lkey)
            .create(temp_ud),
    );

    // register the callbacks
    use rpc_handlers::*;
    rpc_server
        .get_mut_service()
        .register(RPCId::Nil as _, handle_nil);
    rpc_server
        .get_mut_service()
        .register(RPCId::Echo as _, handle_echo);
    rpc_server
        .get_mut_service()
        .register(RPCId::Query as _, handle_query);

    rpc_server
        .get_mut_service()
        .register(RPCId::RemoteRegister as _, handle_remote_register);
    // register msg buffers
    // pre-most receive buffers
    for _ in 0..2048 {
        // 64 is the header
        match rpc_server.post_msg_buf(UDMsg::new(4096, 73)) {
            Ok(_) => {}
            Err(e) => crate::log::error!("post recv buf err: {:?}", e),
        }
    }
    RPC_HANDLER_READY_NUM.fetch_add(1, core::sync::atomic::Ordering::SeqCst);

    let mut counter = 0;
    let mut timer = KTimer::new();

    while !kthread::should_stop() {
        match rpc_server.poll() {
            Ok(Async::Ready(_)) => {}
            Ok(_NotReady) => {}
            Err(e) => crate::log::error!(
                    "RPC handler {} meets an error {:?}, status {:?}",
                    arg.id,
                    e,
                    rpc_server
                ),
        };
        counter += 1;
        if core::intrinsics::unlikely(counter > YIELD_THRESHOLD) {
            if core::intrinsics::unlikely(timer.get_passed_usec() > YIELD_TIME_USEC) {
                kthread::yield_now();
                timer.reset();
            }
            counter = 0;
        }
    }

    crate::log::info!(
            "DMERGE RPC thread {} ended. rpc status: {:?} ",
            arg.id,
            rpc_server
        );
    0
}


pub mod rpc_handlers {
    use mitosis::os_network::bytes::BytesMut;
    use core::fmt::Write;
    use mitosis::linux_kernel_module;
    use mitosis::os_network::serialize::Serialize;

    #[derive(Debug)]
    #[repr(usize)]
    pub(crate) enum RPCId {
        // for test only
        Nil = 1,
        // for test only
        Echo = 2,
        // Resume fork by fetching remote descriptor
        Query = 3,
        // Call for remote register. Used for `Pull` based communication
        RemoteRegister = 4,
    }

    #[derive(Debug, Default, Copy, Clone)]
    pub(crate) struct HeapDescriptorQueryReply {
        pub(crate) pa: u64,
        pub(crate) sz: usize,
        pub(crate) ready: bool,
    }

    impl mitosis::os_network::serialize::Serialize for HeapDescriptorQueryReply {}

    pub(crate) fn handle_nil(_input: &BytesMut, _output: &mut BytesMut) -> usize {
        64
    }

    pub(crate) fn handle_echo(input: &BytesMut, output: &mut BytesMut) -> usize {
        crate::log::info!("echo callback {:?}", input);
        write!(output, "Hello from DMERGE").unwrap();
        64
    }

    pub(crate) fn handle_query(input: &BytesMut, output: &mut BytesMut) -> usize {
        let mut key: usize = 0;

        let heap_service = unsafe { crate::get_shs_mut() };
        unsafe { input.memcpy_deserialize(&mut key) };

        let buf = heap_service.query_descriptor_buf(key);
        if buf.is_none() {
            crate::log::error!("empty addr, key:{}!", key);
            return 0;
        }
        let reply = match buf {
            Some((addr, len)) => {
                HeapDescriptorQueryReply {
                    pa: addr.get_pa(),
                    sz: len,
                    ready: true,
                }
            }
            None => {
                crate::log::error!("Failed to find the handler with id: {}!", key);
                HeapDescriptorQueryReply {
                    pa: 0,
                    sz: 0,
                    ready: false,
                }
            }
        };
        reply.serialize(output);
        return reply.serialization_buf_len();
    }

    #[derive(Debug, Default, Copy, Clone)]
    pub(crate) struct RegisterRemoteReq {
        pub(crate) pa: u64,
        pub(crate) sz: usize,
        /* Original machine id of the actual heap */
        pub(crate) source_machine_id: usize,
        pub(crate) ready: bool,
    }

    #[derive(Debug, Default, Copy, Clone)]
    pub(crate) struct RegisterRemoteReply {
        pub(crate) heap_hint: isize,
    }

    impl mitosis::os_network::serialize::Serialize for RegisterRemoteReq {}

    impl mitosis::os_network::serialize::Serialize for RegisterRemoteReply {}


    pub(crate) fn handle_remote_register(input: &BytesMut, output: &mut BytesMut) -> usize {
        let mut req: RegisterRemoteReq = Default::default();
        unsafe { input.memcpy_deserialize(&mut req) };
        // One-sided RDMA read to fetch heap descriptor and apply it.
        let heap_hint = handle_remote_register_fetch_apply(&req);
        if heap_hint < 0 {
            return 0;
        }
        let reply = RegisterRemoteReply { heap_hint: heap_hint };
        reply.serialize(output);
        return reply.serialization_buf_len();
    }

    fn handle_remote_register_fetch_apply(register_remote_req: &RegisterRemoteReq) -> isize {
        use crate::remote_descriptor_fetch;
        use mitosis::os_network::bytes::ToBytes;
        use mitosis::remote_paging::AccessInfo;
        use crate::descriptors::heap::HeapDescriptor;
        let cpu_id = mitosis::get_calling_cpu_id();
        let source_machine_id = register_remote_req.source_machine_id;
        unsafe { crate::global_locks::get_ref()[cpu_id].lock() };
        let caller = unsafe {
            mitosis::rpc_caller_pool::CallerPool::get_global_caller(cpu_id)
                .expect("the caller should be properly initialized")
        };
        let remote_session_id = unsafe {
            mitosis::startup::calculate_session_id(
                source_machine_id as _,
                cpu_id,
                mitosis::get_max_caller_num(),
            )
        };
        let (des_sz, des_pa) = (register_remote_req.sz, register_remote_req.pa);
        let desc_buf = remote_descriptor_fetch(des_sz,
                                               des_pa,
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
        // TODO: apply to file. Where to store the `file` ?
        // TODO: Walk all of the data for touch. Will it be so time consuming ?
        unsafe { crate::global_locks::get_ref()[cpu_id].unlock() };
        return 1048;
    }
}


