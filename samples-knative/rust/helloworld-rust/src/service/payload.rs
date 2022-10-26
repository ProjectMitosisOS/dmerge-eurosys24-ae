use libc::c_char;
use serde::Serialize;


#[derive(Clone, Serialize)]
pub struct ExampleStruct {
    pub number: u64,
}

#[derive(Clone, Serialize)]
pub struct DataSourcePayload {
    pub id: u64,
    pub uhash: u64,
}
