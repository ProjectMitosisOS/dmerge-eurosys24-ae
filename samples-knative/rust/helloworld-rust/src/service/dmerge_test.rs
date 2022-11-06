use std::ffi::CString;
use std::intrinsics::size_of;
use std::time::{SystemTime, UNIX_EPOCH};
use actix_protobuf::ProtoBufResponseBuilder;
use actix_web::{get, HttpRequest, HttpResponse, HttpResponseBuilder, web};
use actix_web::http::StatusCode;
use libc::{c_char, tm};
use serde_json::{json};


/// Fetch origin data
///
/// Refer of string conversion: https://gist.github.com/jimmychu0807/9a89355e642afad0d2aeda52e6ad2424
#[get("/dmerge/register")]
pub async fn dmerge_register(req: HttpRequest,
                             mut _payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    let qs = qstring::QString::from(req.query_string());
    let size_str = qs.get("size").unwrap_or("1024");
    let mem_sz: usize = size_str.parse::<usize>().expect("parse err");

    // critical path
    let _ = crate::service::bench::dmerge_register_core(
        mem_sz as _, &Default::default());

    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"status": 0})))
}

#[get("/dmerge/pull")]
pub async fn dmerge_pull(req: HttpRequest,
                         mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    let qs = qstring::QString::from(req.query_string());
    let data_loc_address_str = qs.get("addr").unwrap_or("0x4ffff5a00000");
    let hint_str = qs.get("hint").unwrap_or("73");

    let data_loc_address: u64 = hex_str_to_val(&String::from(data_loc_address_str));
    let hint = hint_str.parse::<u32>().expect("not valid digital");

    let start_tick = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards")
        .as_nanos();
    let sd = unsafe { crate::bindings::sopen() };

    unsafe {
        let res = crate::bindings::call_pull(sd, hint, 0);
        let example = crate::read_data::<ExampleStruct>(data_loc_address);

        let mut sum = 0;
        for num in example.vec_data.iter() {
            sum += *num as u64;
        }
        println!("After pull data is:{}, sum is: {}", example.number, sum);
    }

    let end_tick = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards")
        .as_nanos();
    let passed_ns = end_tick - start_tick;
    println!("passed {} ms", passed_ns as f64 / 1000_000 as f64);

    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"data": 0})))
}


#[get("/json/micro")]
pub async fn json_micro(req: HttpRequest,
                        mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    let qs = qstring::QString::from(req.query_string());
    let size_str = qs.get("size").unwrap_or("1024");
    let data_type = qs.get("type").unwrap_or("json");
    let mem_sz: usize = size_str.parse::<usize>().expect("parse err");

    let start_tick = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards")
        .as_nanos();

    let data = "86967897737416471853297327050364959";
    let res = reqwest::Client::new()
        .get(format!("http://localhost:{}/{}/data?size={}",
                     crate::server_port(), data_type, mem_sz.to_string()))
        .json(&crate::MapperRequest { chunk_data: String::from(data) })
        .send().await;
    if res.is_err() {
        println!("not success");
    } else {
        let _t = res.expect("").text();
    }

    let end_tick = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards")
        .as_nanos();
    let passed_ns = end_tick - start_tick;
    println!("passed {} ms", passed_ns as f64 / 1000_000 as f64);
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"user": "python"})))
}

#[get("/json/data")]
pub async fn json_data(req: HttpRequest,
                       mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    let qs = qstring::QString::from(req.query_string());
    let size_str = qs.get("size").unwrap_or("1024");
    let mem_sz: usize = size_str.parse::<usize>().expect("parse err");

    let mut arr: Vec<u32> = Vec::with_capacity(mem_sz);
    for i in 0..mem_sz / 4 {
        arr.push(1);
    }
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"tick": serde_json::to_string(&arr).expect("to string failed")})))
}
include!(concat!(env!("OUT_DIR"), "/protos/mod.rs"));
use protobuf::Message;
use crate::{AllocatorMaster, get_global_allocator_master_mut, jemalloc_alloc, jemalloc_free, JemallocAllocator};
use crate::service::payload::ExampleStruct;
use crate::sys_env::{heap_base, hex_str_to_val};

#[get("/protobuf/data")]
pub async fn protobuf_data(req: HttpRequest,
                           mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    #[inline]
    pub fn gen_arr_message(mem_size: usize) -> example::ArrMessage {
        use example::{ArrMessage};
        let mut msg = ArrMessage::new();
        let arr_len = mem_size / size_of::<i32>();
        for i in 0..arr_len {
            msg.data.push(i as i32);
        }
        return msg;
    }

    let qs = qstring::QString::from(req.query_string());
    let size_str = qs.get("size").unwrap_or("1024");
    let mem_sz: usize = size_str.parse::<usize>().expect("parse err");

    let arr_message = gen_arr_message(mem_sz as _);
    let out_bytes: Vec<u8> = arr_message.write_to_bytes().expect("write err");
    Ok(HttpResponseBuilder::new(StatusCode::OK).protobuf(out_bytes).unwrap())
}