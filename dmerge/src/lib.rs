#![no_std]

/// Distributed Merge: A set of os primitive for message passing.
extern crate alloc;

mod core_syscall_handler;
/// Import MITOSIS
pub use mitosis;
pub use mitosis::KRdmaKit;
pub use mitosis::log;
