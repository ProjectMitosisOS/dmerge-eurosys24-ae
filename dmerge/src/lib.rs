#![no_std]
#![feature(
core_intrinsics,
allocator_api,
nonnull_slice_from_raw_parts,
alloc_layout_extra,
get_mut_unchecked,
trait_alias,
)]
/// Distributed Merge: A set of os primitive for message passing.
extern crate alloc;

pub mod core_syscall_handler;
pub mod descriptors;
pub mod shadow_heap;
/// Import MITOSIS
pub use mitosis;
pub use mitosis_macros;
pub use mitosis::KRdmaKit;
pub use mitosis::log;
pub use mitosis::bindings;
