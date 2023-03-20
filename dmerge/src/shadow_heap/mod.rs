use alloc::sync::Arc;
use alloc::vec::Vec;
use mitosis::linux_kernel_module;
use mitosis::os_network::rdma::dc::DCTarget;

use vma::ShadowVMA;
use core::sync::atomic::compiler_fence;
use core::sync::atomic::Ordering::SeqCst;
use hashbrown::HashMap;
use mitosis::descriptors::RDMADescriptor;
use mitosis::kern_wrappers::mm::VirtAddrType;

pub mod vma;
pub mod heap;

pub use heap::ShadowHeap;
use mitosis::os_network::{msg::UDMsg as RMemory, serialize::Serialize};
use mitosis::os_network::bytes::ToBytes;
use crate::descriptors::HeapMeta;

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

impl Drop for ShadowHeapService {
    fn drop(&mut self) {
        self.registered_heap.clear();
    }
}

impl ShadowHeapService {
    pub fn query_descriptor_buf(&self, key: usize) -> core::option::Option<(&RMemory, usize)> {
        self.registered_heap
            .get(&key)
            .map(|s| (&s.serialized_buf, s.serialized_buf_len))
    }

    pub fn query_descriptor(
        &self,
        key: usize,
    ) -> core::option::Option<&mitosis::descriptors::ParentDescriptor> {
        self.registered_heap
            .get(&key)
            .map(|s| s.heap.get_descriptor_ref())
    }
}

impl ShadowHeapService {
    pub fn register_heap(&mut self, key: usize, heap_start_addr: VirtAddrType) -> core::option::Option<usize> {
        let (target, descriptor) = RDMADescriptor::new_from_dc_target_pool().unwrap();

        // create bundler
        let bundler = HeapBundler::new(
            ShadowHeap::new(descriptor,
                            HeapMeta { start_virt_addr: heap_start_addr }),
            target,
        );

        self.add_bundler(key, bundler)
    }

    pub fn unregister(&mut self, key: usize) {
        self.registered_heap.remove(&key);
    }


    #[inline]
    fn add_bundler(&mut self,
                   key: usize,
                   bundler: HeapBundler) -> core::option::Option<usize> {
        let seri_buf_len = bundler.get_serialize_buf_sz();
        self.registered_heap.insert(key, bundler);
        return Some(seri_buf_len);
    }
}