use mitosis::kern_wrappers::mm::{VirtAddrType};

pub mod heap;

#[derive(Clone, Default)]
pub struct HeapMeta {
    pub start_virt_addr: VirtAddrType,
    pub heap_size: u64,
}

