use std::collections::HashMap;
use std::intrinsics::size_of;
use std::time::{SystemTime, UNIX_EPOCH};
use crate::JemallocAllocator;
use crate::service::cloud_event::*;
use crate::service::payload::ExampleStruct;
use crate::sys_env::heap_hint;

#[derive(Clone)]
pub struct BenchObj {
    pub number: u64,
    pub vec_data: Vec<u32, JemallocAllocator>,
}

impl Default for BenchObj {
    fn default() -> Self {
        Self { number: 0, vec_data: Vec::new_in(JemallocAllocator) }
    }
}


// Prepare for data, and return address
pub fn dmerge_register_core(payload_sz: u64,
                            meta: &HashMap<String, String>) -> HashMap<String, String> {
    let bbox =
        unsafe { crate::init_jemalloc_box::<BenchObj>() };
    let base_addr
        = bbox.as_ptr() as u64;

    let obj =
        unsafe { crate::read_data::<BenchObj>(base_addr) };

    type EntryType = u32;
    let mut vec: Vec<EntryType, JemallocAllocator> = Vec::new_in(JemallocAllocator);
    let len = payload_sz / (size_of::<EntryType>() as u64);
    for _i in 0..len {
        vec.push(1);
    }

    obj.vec_data = vec;
    obj.number = 4124;
    println!("data is:{}, len is:{}, addr is: 0x{:x}",
             obj.number, obj.vec_data.len(), base_addr);

    let mut data = meta.clone();

    // Gid as network address
    data.insert(DATA_NW_ADDR_KEY.to_string(),
                format!("fe80:0000:0000:0000:248a:0703:009c:7ca0"));
    // Base address
    data.insert(DATA_DATA_LOC_KEY.to_string(), base_addr.to_string());
    data.insert(DATA_HINT_KEY.to_string(), heap_hint().to_string());

    // Profiling data
    let since_the_epoch = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards");
    data.insert(PROFILE_START_TICK.to_string(), since_the_epoch.as_nanos().to_string());


    data
}

pub fn dmerge_pull_core() {
    unimplemented!()
}
