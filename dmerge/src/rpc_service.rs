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
        .register(RPCId::Query as _, hanlde_query);

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

    pub(crate) fn hanlde_query(input: &BytesMut, output: &mut BytesMut) -> usize {
        let mut key: usize = 0;

        let heap_service = unsafe { crate::get_shs_mut() };
        unsafe { input.memcpy_deserialize(&mut key) };

        let buf = heap_service.query_descriptor_buf(key);
        if buf.is_none() {
            crate::log::error!("empty addr, key:{}!", key);
            return 0;
        }
        let reply = match buf {
            Some((addr,len)) => {
                HeapDescriptorQueryReply{
                    pa: addr.get_pa(),
                    sz: len,
                    ready: true
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
}


