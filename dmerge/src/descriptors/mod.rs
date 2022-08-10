use mitosis::kern_wrappers::mm::PhyAddrType;

pub mod heap;

#[derive(Clone, Default)]
pub struct HeapMeta {
    pub start_phy_addr: PhyAddrType,
    pub heap_size: u64,
}

