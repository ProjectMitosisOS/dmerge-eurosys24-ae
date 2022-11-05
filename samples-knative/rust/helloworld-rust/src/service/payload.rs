use libc::c_char;
use serde::{Serialize, Serializer};
use crate::JemallocAllocator;


#[derive(Clone)]
pub struct ExampleStruct {
    pub number: u64,
    pub vec_data: Vec<u32, JemallocAllocator>,
}

impl Default for ExampleStruct {
    fn default() -> Self {
        Self { number: 0, vec_data: Vec::new_in(JemallocAllocator) }
    }
}

#[derive(Clone, Serialize)]
pub struct DmergeStruct {
    pub number: u64,
}

#[derive(Clone, Serialize)]
pub struct DataSourcePayload {
    pub id: u64,
    pub uhash: u64,
}
