use mitosis::descriptors::{RDMADescriptor, RegDescriptor, VMADescriptor};
use alloc::vec::Vec;
use mitosis::kern_wrappers::mm::{PhyAddrType, VirtAddrType};
use mitosis::kern_wrappers::task::Task;
use mitosis::os_network::bytes::BytesMut;
use mitosis::remote_mapping::{PhysAddr, RemotePageTable, VirtAddr};
use mitosis::remote_paging::AccessInfo;
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
    pub fn apply_to(&mut self, file: *mut mitosis::bindings::file, eager_fetch: bool) {
        let task = Task::new();
        if eager_fetch {
            let access_info = AccessInfo::new(&self.machine_info).unwrap();
            self.vma.clone().into_iter().enumerate().for_each(|(i, m)| {
                // ensure only map into the heap space
                let vma = unsafe {
                    task.map_one_region(file, &m,
                                        self.vma.get(i + 1))
                };

                if let Some(vma) = vma {
                    unsafe {
                        vma.vm_flags = (mitosis::bindings::VMFlags::from_bits_unchecked(vma.vm_flags)
                            | mitosis::bindings::VMFlags::MIXEDMAP)
                            .bits()
                    };
                    // tune the bits
                    let origin_vma_flags =
                        unsafe { mitosis::bindings::VMFlags::from_bits_unchecked(m.flags) };
                    // crate::log::info!("orign vma: {:?}", origin_vma_flags);
                    if origin_vma_flags.contains(mitosis::bindings::VMFlags::VM_ALLOC) {
                        // set the vma
                        mitosis::kern_wrappers::vma::VMA::new(vma).set_alloc();
                    }
                    // Eager fetch from remote
                    self.eager_fetch_vma(&m, vma, &access_info);
                } else {
                    crate::log::debug!("not map success on vma (start 0x{:x}, sz {}) ",
                    m.get_start(), m.get_sz());
                }
            });
        } else {
            (&self.vma).into_iter().enumerate().for_each(|(i, m)| {
                // ensure only map into the heap space
                let vma = unsafe {
                    task.map_one_region(file, m,
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
        }
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

impl HeapDescriptor {
    fn eager_fetch_vma(
        &mut self,
        vma_des: &VMADescriptor,
        vma: &'static mut mitosis::bindings::vm_area_struct,
        access_info: &AccessInfo,
    ) {
        let (size, start) = (vma_des.get_sz(), vma_des.get_start());
        let len = 12;
        let mut addr_buf: Vec<VirtAddrType> = Vec::with_capacity(len);
        for addr in (start..start + size).step_by(4096) {
            if addr_buf.len() < len {
                addr_buf.push(addr);
            }
            if len == addr_buf.len() {
                // batch
                let page_list = self.batch_read_remote_pages(&addr_buf, access_info);

                for (i, new_page_p) in page_list.iter().enumerate() {
                    if let Some(new_page_p) = new_page_p {
                        vma.vm_page_prot.pgprot =
                            vma.vm_page_prot.pgprot | (((1 as u64) << 52) as u64); // present bit
                        let _ = unsafe {
                            mitosis::bindings::pmem_vm_insert_page(vma, addr_buf[i], *new_page_p)
                        };
                        // self.eager_fetched_pages.insert(*new_page_p as VirtAddrType);
                    }
                }
                addr_buf.clear();
            }
        }
        if !addr_buf.is_empty() {
            // batch
            let page_list = self.batch_read_remote_pages(&addr_buf, access_info);

            for (i, new_page_p) in page_list.iter().enumerate() {
                if let Some(new_page_p) = new_page_p {
                    vma.vm_page_prot.pgprot = vma.vm_page_prot.pgprot | (((1 as u64) << 52) as u64); // present bit
                    let _ = unsafe {
                        mitosis::bindings::pmem_vm_insert_page(vma, addr_buf[i], *new_page_p)
                    };
                    // self.eager_fetched_pages.insert(*new_page_p as VirtAddrType);
                }
            }
        }
    }
    #[inline]
    #[allow(dead_code)]
    fn batch_read_remote_pages(
        &self,
        addr_list: &Vec<VirtAddrType>,
        access_info: &AccessInfo,
    ) -> Vec<Option<*mut crate::mitosis::bindings::page>> {
        use mitosis::os_network::Conn;
        use mitosis::os_network;
        let mut res: Vec<Option<*mut mitosis::bindings::page>> = Vec::with_capacity(addr_list.len());
        for (i, remote_va) in addr_list.iter().enumerate() {
            let remote_pa = self.lookup_pg_table(*remote_va);
            if remote_pa.is_none() {
                res.push(None);
                continue;
            }

            let new_page_p =
                unsafe { mitosis::bindings::pmem_alloc_page(mitosis::bindings::PMEM_GFP_HIGHUSER) };
            let new_page_pa = unsafe { mitosis::bindings::pmem_page_to_phy(new_page_p) } as u64;

            let result = {
                use mitosis::KRdmaKit::rust_kernel_rdma_base::bindings::*;
                let (dst, src, sz) = (new_page_pa, remote_pa.unwrap(), 4096);
                let flag = if i == addr_list.len() - 1 {
                    ib_send_flags::IB_SEND_SIGNALED
                } else {
                    0
                };
                let pool_idx = unsafe { mitosis::bindings::pmem_get_current_cpu() } as usize;
                let (dc_qp, lkey) =
                    unsafe { mitosis::get_dc_pool_service_mut().get_dc_qp_key(pool_idx) }
                        .expect("failed to get DCQP");

                let mut payload = mitosis::remote_paging::DCReqPayload::default()
                    .set_laddr(dst)
                    .set_raddr(PhysAddr::decode(src)) // copy from src into dst
                    .set_sz(sz as _)
                    .set_lkey(*lkey)
                    .set_rkey(access_info.rkey)
                    .set_send_flags(flag)
                    .set_opcode(ib_wr_opcode::IB_WR_RDMA_READ)
                    .set_ah_ptr(unsafe { access_info.ah.get_inner() })
                    .set_dc_access_key(access_info.dct_key as _)
                    .set_dc_num(access_info.dct_num);

                let mut payload = unsafe { core::pin::Pin::new_unchecked(&mut payload) };
                os_network::rdma::payload::Payload::<ib_dc_wr>::finalize(payload.as_mut());

                // now sending the RDMA request
                let res = dc_qp.post(&payload.as_ref());
                if res.is_err() {
                    crate::log::error!("failed to batch read pages {:?}", res);
                }

                if i == addr_list.len() - 1 {
                    // wait for the request to complete
                    let mut timeout_dc = os_network::timeout::TimeoutWRef::new(
                        dc_qp,
                        mitosis::remote_paging::TIMEOUT_USEC,
                    );
                    match mitosis::os_network::block_on(&mut timeout_dc) {
                        Ok(_) => Ok(()),
                        Err(e) => {
                            if e.is_elapsed() {
                                crate::log::error!("fatal, timeout on reading the DC QP");
                                Err(mitosis::os_network::rdma::Err::Timeout)
                            } else {
                                Err(e.into_inner().unwrap())
                            }
                        }
                    }
                } else {
                    Ok(())
                }
            };

            match result {
                Ok(_) => res.push(Some(new_page_p)),
                Err(e) => {
                    crate::log::error!(
                        "[batch_read_remote_pages] Failed to read the remote page {:?}",
                        e
                    );
                    unsafe { mitosis::bindings::pmem_free_page(new_page_p) };
                    res.push(None)
                }
            }
        }

        return res;
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
