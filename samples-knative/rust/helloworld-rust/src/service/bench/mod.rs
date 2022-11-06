use std::collections::HashMap;
use std::intrinsics::size_of;
use std::time::{SystemTime, UNIX_EPOCH};
use crate::JemallocAllocator;
use crate::service::cloud_event::*;
use crate::service::payload::ExampleStruct;
use crate::sys_env::{heap_base, heap_hint};
use serde::{Deserialize, Serialize};

#[derive(Clone)]
pub struct DMergeBenchObj {
    pub number: u64,
    pub vec_data: Vec<u32, JemallocAllocator>,
}


#[derive(Debug, Serialize, Deserialize)]
pub struct SeriBenchObj {
    pub number: u64,
    pub payload: Vec<u32>,
}

impl Default for DMergeBenchObj {
    fn default() -> Self {
        Self { number: 0, vec_data: Vec::new_in(JemallocAllocator) }
    }
}

#[inline]
pub fn cur_tick_nano() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards")
        .as_nanos()
}

// Prepare for data, and return address
pub fn dmerge_register_core(payload_sz: u64) -> u64 {
    let bbox =
        unsafe { crate::init_jemalloc_box::<DMergeBenchObj>() };
    let base_addr
        = bbox.as_ptr() as u64;

    let obj =
        unsafe { crate::read_data::<DMergeBenchObj>(base_addr) };

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

    base_addr
}

pub fn dmerge_pull_core(machine_id: usize,
                        hint: usize,
                        data_loc_address: u64) -> HashMap<String, String> {
    let mut ret_data: HashMap<String, String> = Default::default();

    let sd = unsafe { crate::bindings::sopen() };
    let _ = unsafe { crate::bindings::call_pull(sd, hint as _, machine_id as _) };

    let example = unsafe { crate::read_data::<ExampleStruct>(data_loc_address) };
    let mut sum = 0;

    for item in example.vec_data.iter() {
        sum += *item;
    }
    println!("After pull data is:{}, sum is: {}", example.number, sum);

    ret_data
}
