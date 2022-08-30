use mitosis::descriptors::{CompactPageTable, RDMADescriptor, RegDescriptor, VMADescriptor};
use crate::KRdmaKit::rust_kernel_rdma_base::VmallocAllocator;
use alloc::vec::Vec;
use mitosis::kern_wrappers::mm::{PhyAddrType, VirtAddrType};
use mitosis::kern_wrappers::task::Task;
use mitosis::os_network::bytes::BytesMut;
use mitosis::remote_mapping::{PhysAddr, RemotePageTable, VirtAddr};
use mitosis::remote_paging::AccessInfo;
use crate::descriptors::HeapMeta;
use crate::mitosis::linux_kernel_module;

pub(crate) type Offset = u32;
pub(crate) type Value = PhyAddrType;
/// HeapDescriptor
#[allow(dead_code)]
pub struct HeapDescriptor {
    pub regs: RegDescriptor,
    pub page_table: RemotePageTable,

    pub vma: Vec<VMADescriptor>,
    pub machine_info: RDMADescriptor,
}

impl Default for HeapDescriptor {
    fn default() -> Self {
        Self {
            regs: Default::default(),
            page_table: Default::default(),
            vma: Default::default(),
            machine_info: Default::default(),
        }
    }
}

impl HeapDescriptor {
    #[inline]
    pub fn apply_to(&mut self, file: *mut mitosis::bindings::file) {
        use mitosis::linux_kernel_module;

        let mut task = Task::new();

        (&self.vma).into_iter().enumerate().for_each(|(i, m)| {
            // ensure only map into the heap space
            let mapped_vma: VMADescriptor = VMADescriptor {
                range: (m.get_start(), m.get_end()),
                flags: m.flags,
                prot: m.prot,
                is_anonymous: m.is_anonymous,
            };
            crate::log::debug!("start to map vma start:0x{:x}, end:0x{:x}",
                    mapped_vma.get_start(), mapped_vma.get_end());
            let vma = unsafe {
                task.map_one_region(file, &mapped_vma,
                                    self.vma.get(i + 1))
            };
            if let Some(vma) = vma {
                // tune the bits
                let origin_vma_flags =
                    unsafe { mitosis::bindings::VMFlags::from_bits_unchecked(m.flags) };
                // crate::log::info!("orign vma: {:?}", origin_vma_flags);
                if origin_vma_flags.contains(mitosis::bindings::VMFlags::VM_ALLOC) {
                    // set the vma
                    mitosis::kern_wrappers::vma::VMA::new(vma).set_alloc();
                }
            } else {
                crate::log::debug!("not map success on vma (start 0x{:x}, sz {}) ",
                    m.get_start(), m.get_sz());
            }
        });
        // Note: Do not apply the regs!!!
    }


    #[inline(always)]
    pub fn lookup_pg_table(&self, virt: VirtAddrType) -> Option<PhyAddrType> {
        self.page_table
            .translate(VirtAddr::new(virt))
            .map(|v| v.as_u64())
    }
}

impl HeapDescriptor {
    #[inline]
    pub unsafe fn read_remote_page(
        &mut self,
        remote_va: PhyAddrType,
        access_info: &AccessInfo,
    ) -> Option<*mut mitosis::bindings::page> {
        let remote_pa = self.lookup_pg_table(remote_va);
        if remote_pa.is_none() {
            crate::log::debug!("not find va 0x{:x}", remote_va);
            return None;
        }
        let remote_pa = remote_pa.unwrap();
        let new_page_p = mitosis::bindings::pmem_alloc_page(mitosis::bindings::PMEM_GFP_HIGHUSER);
        let new_page_pa = mitosis::bindings::pmem_page_to_phy(new_page_p) as u64;
        let res = mitosis::remote_paging::RemotePagingService::remote_read(
            new_page_pa,
            remote_pa,
            4096,
            access_info,
        );
        return match res {
            Ok(_) => Some(new_page_p),
            Err(e) => {
                crate::log::error!("Failed to read the remote page {:?}", e);
                mitosis::bindings::pmem_free_page(new_page_p);
                None
            }
        };
    }
}



impl crate::mitosis::os_network::serialize::Serialize for HeapDescriptor {
    fn serialize(&self, _bytes: &mut BytesMut) -> bool {
        unimplemented!();
    }

    /// De-serialize from a message buffer
    /// **Warning**
    /// - The buffer to be serialized must be generated from the ParentDescriptor.
    ///
    /// **TODO**
    /// - Currently, we don't check the buf len, so this function is **unsafe**
    fn deserialize(bytes: &BytesMut) -> core::option::Option<Self> {
        // FIXME: check buf len

        let mut cur = unsafe { bytes.truncate_header(0).unwrap() };

        // regs
        let regs = RegDescriptor::deserialize(&cur)?;
        cur = unsafe { cur.truncate_header(regs.serialization_buf_len())? };

        // VMA page counts
        let mut count: usize = 0;
        let off = unsafe { cur.memcpy_deserialize(&mut count)? };
        cur = unsafe { cur.truncate_header(off)? };

        crate::log::debug!("!!!!! start to deserialize vma, count: {}", count);

        // VMA & its corresponding page table
        let mut pt = RemotePageTable::new();

        let mut vmas = Vec::new();

        for _ in 0..count {
            let vma = VMADescriptor::deserialize(&cur)?;
            cur = unsafe { cur.truncate_header(vma.serialization_buf_len())? };

            let vma_start = vma.get_start();
            vmas.push(vma);

            // now, deserialize the page table of this VMA
            // we don't use the `deserialize` method in the compact page table,
            // because it will incur unnecessary memory copies that is not optimal for the performance
            let mut page_num: usize = 0;
            let off = unsafe { cur.memcpy_deserialize(&mut page_num)? };

            cur = unsafe { cur.truncate_header(off)? };

            // crate::log::debug!("check page_num: {}", page_num);
            /*
            if page_num > 1024 {
                return None;
            }*/

            if core::mem::size_of::<Offset>() < core::mem::size_of::<VirtAddrType>()
                && page_num % 2 == 1
            {
                let mut pad: u32 = 0;
                let off = unsafe { cur.memcpy_deserialize(&mut pad)? };
                cur = unsafe { cur.truncate_header(off)? };
            }

            for _ in 0..page_num {
                let virt: Offset = unsafe { cur.read_unaligned_at_head() };
                cur = unsafe { cur.truncate_header(core::mem::size_of::<Offset>())? };

                let phy: Value = unsafe { cur.read_unaligned_at_head() };
                cur = unsafe { cur.truncate_header(core::mem::size_of::<Value>())? };

                pt.map(
                    VirtAddr::new(virt as VirtAddrType + vma_start),
                    PhysAddr::new(phy),
                );
            }
        }

        let machine_info = RDMADescriptor::deserialize(&cur)?;

        Some(Self {
            regs: regs,
            page_table: pt,
            vma: vmas,
            machine_info: machine_info,
        })
    }

    fn serialization_buf_len(&self) -> usize {
        unimplemented!();
        /*
        self.regs.serialization_buf_len()
            + self.page_table.serialization_buf_len()
            + core::mem::size_of::<usize>() // the number of VMA descriptors
            + self.vma.len() * core::mem::size_of::<VMADescriptor>()
            + self.machine_info.serialization_buf_len() */
    }
}
