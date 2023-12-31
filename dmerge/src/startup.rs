use mitosis::Config;
use mitosis::startup::init_mitosis;
use mitosis::linux_kernel_module;
use mitosis::rpc_service::Service;
use mitosis::rpc_caller_pool::CallerPool;

fn start_instance(config: &Config) -> core::option::Option<()> {
    init_mitosis(config)?;
    init_rpc(config, crate::rpc_service::worker)?;
    // global lock
    {
        use alloc::vec::Vec;
        let mut locks = Vec::new();
        for _ in 0..config.max_core_cnt {
            locks.push(mitosis::linux_kernel_module::mutex::LinuxMutex::new(()));
        }

        for i in 0..locks.len() {
            locks[i].init();
        }

        unsafe { crate::global_locks::init(locks) };
    }

    {
        unsafe {crate::heap_id_generator::init(crate::id_generator::IdFactory::create())}
    }

    Some(())
}

fn init_rpc(config: &Config,
            rpc_worker: extern "C" fn(*mut mitosis::linux_kernel_module::c_types::c_void) -> i32) -> core::option::Option<()> {
    // RPC service
    unsafe {
        mitosis::set_service_rpc(
            Service::new_with_worker(config, rpc_worker).expect("Failed to create the RPC service. "),
        );
    };
    crate::log::info!("RPC service initializes done");

    // RPC caller pool
    unsafe {
        mitosis::set_rpc_caller_pool(
            CallerPool::new(config)
                .expect("Failed to create the RPC caller pool"),
        );
    };

    crate::log::info!("Start waiting for the RPC servers to start...");
    crate::rpc_service::wait_handlers_ready_barrier(config.rpc_threads_num);
    crate::log::info!("All RPC thread handlers initialized!");

    Some(())
}

/// Body function for starting the DMerge.
pub fn start_dmerge(config: &Config) -> core::option::Option<()> {
    unsafe {
        crate::sh_service::init(Default::default());

        // mitosis::startup::start_instance(config.clone())

        // dmerge start instance
        start_instance(config)
    }
}

pub fn end_dmerge() {
    unsafe {
        crate::sh_service::drop();
        crate::global_locks::drop();
        crate::heap_id_generator::drop();
        mitosis::startup::end_instance();
    };
}