use libc::c_char;


#[derive(Clone)]
pub struct ExampleStruct {
    pub number: u64,
    pub name: *const c_char,
}

#[derive(Clone)]
pub struct DataSourcePayload {
    pub id: u64,
    pub uhash: u64,
    pub context_text: *const c_char,
}
