use std::collections::HashMap;
use std::intrinsics::size_of;
use std::time::{SystemTime, UNIX_EPOCH};
use crate::JemallocAllocator;
use crate::service::payload::ExampleStruct;
use serde::{Deserialize, Serialize};
use tokio::time::Instant;

pub type DigitialBenchEntryType = u32;


#[derive(Clone)]
pub struct DMergeDigitalBenchObj {
    pub number: u64,
    pub vec_data: Vec<DigitialBenchEntryType, JemallocAllocator>,
}


#[derive(Debug, Serialize, Deserialize)]
pub struct SeriDigitialBenchObj {
    pub number: u64,
    pub payload: Vec<DigitialBenchEntryType>,
}

impl Default for DMergeDigitalBenchObj {
    fn default() -> Self {
        Self { number: 0, vec_data: Vec::new_in(JemallocAllocator) }
    }
}

#[derive(Clone)]
pub struct DMergeWCBenchObj {
    pub words: Vec<String, JemallocAllocator>,
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
        unsafe { crate::init_jemalloc_box::<DMergeDigitalBenchObj>() };
    let base_addr
        = bbox.as_ptr() as u64;

    let obj =
        unsafe { crate::read_data::<DMergeDigitalBenchObj>(base_addr) };

    let mut vec: Vec<DigitialBenchEntryType, JemallocAllocator> = Vec::new_in(JemallocAllocator);
    let len = payload_sz / (size_of::<DigitialBenchEntryType>() as u64);
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
    println!("[Pull Core] machine id: {}, hint: {}, addr base: 0x{:x}",
             machine_id, hint, data_loc_address);
    let ret_data: HashMap<String, String> = Default::default();
    let start = Instant::now();

    let sd = unsafe { crate::bindings::sopen() };
    let _ = unsafe { crate::bindings::call_pull(sd, hint as _, machine_id as _) };
    println!("[pull meta] {} ms", (Instant::now() - start).as_micros() as f64 / 1000.0);

    let start = Instant::now();

    let example = unsafe { crate::read_data::<ExampleStruct>(data_loc_address) };
    let mut sum = 0;

    for item in example.vec_data.iter() {
        sum += *item;
    }
    println!("[pull data] {} ms", (Instant::now() - start).as_micros() as f64 / 1000.0);

    println!("After pull data is: {}, sum is: {}", example.number, sum);

    ret_data
}
