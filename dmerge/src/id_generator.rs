use mitosis::linux_kernel_module::mutex::LinuxMutex;
use mitosis::linux_kernel_module::sync::Mutex;

pub struct IdFactory {
    cur_id: LinuxMutex<u64>,
}

impl IdFactory {
    pub fn create() -> Self {
        Self { cur_id: LinuxMutex::new(0) }
    }

    #[inline]
    pub fn alloc_one_id(&mut self) -> u64 {
        self.cur_id.lock_f(|id| {
            *id += 1;
            *id as u64
        })
    }
}