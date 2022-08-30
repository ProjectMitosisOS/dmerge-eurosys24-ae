use alloc::sync::Arc;
use alloc::vec::Vec;
use mitosis::descriptors::{CompactPageTable, RDMADescriptor};
use mitosis::kern_wrappers::task::Task;
use mitosis::KRdmaKit::rust_kernel_rdma_base::VmallocAllocator;
use mitosis::shadow_process::{COW4KPage, ShadowPageTable};
use mitosis::linux_kernel_module;
use mitosis::os_network::rdma::dc::DCTarget;

use crate::descriptors::heap::HeapDescriptor;
use crate::shadow_heap::vma::VMAPTGenerator;
use crate::log;
use vma::ShadowVMA;
use crate::descriptors::HeapMeta;
use core::sync::atomic::compiler_fence;
use core::sync::atomic::Ordering::SeqCst;
use hashbrown::HashMap;

pub mod vma;
pub mod heap;

pub use heap::ShadowHeap;
use mitosis::os_network::{msg::UDMsg as RMemory, serialize::Serialize};
use mitosis::os_network::bytes::ToBytes;

pub struct HeapBundler {
    #[allow(dead_code)]
    pub heap: ShadowHeap,
    serialized_buf: RMemory,
    serialized_buf_len: usize,

    #[allow(dead_code)]
    bound_dc_targets: Vec<Arc<DCTarget>>,
}


impl HeapBundler {
    pub fn new(heap: ShadowHeap, targets: Arc<DCTarget>) -> Self {
        use mitosis::linux_kernel_module;
        let len = heap.get_descriptor_ref().serialization_buf_len();
        crate::log::debug!(
            "Alloc serialization buf sz {} KB",
            len / 1024
        );
        let mut buf = unsafe { mitosis::get_mem_pool_mut() }.pop_one();
        crate::log::debug!("serialization buf allocation done!");

        heap.get_descriptor_ref().serialize(buf.get_bytes_mut());
        compiler_fence(SeqCst);

        crate::log::debug!("Heap bundle descriptor len: {}", buf.len());

        let mut bound_targets = Vec::new();
        bound_targets.push(targets);

        Self {
            heap: heap,
            serialized_buf: buf,
            serialized_buf_len: len,
            bound_dc_targets: bound_targets,
        }
    }

    fn get_serialize_buf_sz(&self) -> usize {
        self.serialized_buf.len()
    }
}

pub struct ShadowHeapService {
    registered_heap: HashMap<usize, HeapBundler>,
}

impl Default for ShadowHeapService {
    fn default() -> Self {
        Self {
            registered_heap: Default::default()
        }
    }
}

impl ShadowHeapService {
    pub fn add_bundler(&mut self,
                       key: usize,
                       bundler: HeapBundler) -> core::option::Option<usize> {
        self.registered_heap.insert(key, bundler);

        return Some(0);
    }

    pub fn unregister(&mut self, key: usize) {
        self.registered_heap.remove(&key);
    }
}