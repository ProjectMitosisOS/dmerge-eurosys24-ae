#[allow(
clippy::all,
non_camel_case_types,
non_upper_case_globals,
non_snake_case,
improper_ctypes,
non_upper_case_globals,
dead_code
)]
mod bindings {
    use crate::mitosis::linux_kernel_module::c_types;
    include!(concat!(env!("OUT_DIR"), "/bindings-dmerge.rs"));
}
pub use bindings::*;
