use mitosis::linux_kernel_module::c_types::c_long;
use mitosis::bindings;

#[allow(dead_code)]
pub struct DMergeSyscallHandler {
    my_file: *mut bindings::file,
}

impl Drop for DMergeSyscallHandler {
    fn drop(&mut self) {}
}

impl DMergeSyscallHandler {
    pub fn syscall_mem_push(&mut self) -> c_long {
        0
    }
}