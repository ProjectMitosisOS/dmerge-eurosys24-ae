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

    let start_tick = crate::service::bench::cur_tick_nano();

    // critical path
    let data_loc = crate::service::bench::dmerge_register_core(
        mem_sz as _);

    // merge
    {
        let url = format!("http://localhost:8090/dmerge/pull?addr=0x{:x}",
                          data_loc);
        let res = reqwest::Client::new()
            .get(url)
            .json(&crate::MapperRequest { chunk_data: "chunk data".parse()? })
            .send().await;
        if res.is_err() {
            println!("not success");
        } else {
            let _t = res.expect("").text();
        }
    }
    let end_tick = crate::service::bench::cur_tick_nano();
    let passed_ns = end_tick - start_tick;
    println!("[Bench] Passed {} ms", passed_ns as f64 / 1000_000 as f64);

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

    // critical path
    let ret_data = crate::service::bench::dmerge_pull_core(0,
                                                           hint as _,
                                                           data_loc_address);
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

    let start_tick = crate::service::bench::cur_tick_nano();

    let data = "86967897737416471853297327050364959";
    let res = reqwest::Client::new()
        .get(format!("http://localhost:{}/{}/data?size={}",
                     crate::server_port(), data_type, mem_sz.to_string()))
        .json(&crate::MapperRequest { chunk_data: String::from("86967897737416471853297327050364959") })
        .send().await;
    if res.is_err() {
        println!("not success");
    } else {
        let bytes = res.expect("fail to get reply").bytes().await.expect("fail to get bytes").to_vec();
        match data_type {
            "json" => {
                let v = serde_json::from_slice::<crate::service::bench::SeriBenchObj>(bytes.as_slice())
                    .expect("unwrap");

                let mut sum = 0;
                for item in v.payload.iter() {
                    sum += *item;
                }
                println!("len: {}, and sum: {}", v.payload.len(), sum);
            }
            "protobuf" => {
                use example::{ArrMessage};
                let msg = ArrMessage::parse_from_bytes(bytes.as_slice()).expect("not valid struct");
                let mut sum = 0;
                for item in msg.data.iter() {
                    sum += *item;
                }
                println!("len: {}, and sum: {}", msg.data.len(), sum);
            }
            _ => unimplemented!()
        };
    }

    let end_tick = crate::service::bench::cur_tick_nano();
    let passed_ns = end_tick - start_tick;
    println!("[Bench] Passed {} ms", passed_ns as f64 / 1000_000 as f64);
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"status": 0})))
}

#[get("/json/data")]
pub async fn json_data(req: HttpRequest,
                       mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    type EntryType = u32;

    let qs = qstring::QString::from(req.query_string());
    let size_str = qs.get("size").unwrap_or("1024");
    let mem_sz: usize = size_str.parse::<usize>().expect("parse err");
    let mut arr: Vec<EntryType> = Vec::with_capacity(mem_sz);
    let len = mem_sz as u64 / (size_of::<EntryType>() as u64);

    for _i in 0..len {
        arr.push(1);
    }
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(&crate::service::bench::SeriBenchObj { number: 1024, payload: arr }))
}
include!(concat!(env!("OUT_DIR"), "/protos/mod.rs"));
use protobuf::Message;
use crate::{AllocatorMaster, get_global_allocator_master_mut, jemalloc_alloc, jemalloc_free, JemallocAllocator};
use crate::service::bench::DMergeBenchObj;
use crate::service::cloud_event::{DATA_DATA_LOC_KEY, PROFILE_START_TICK};
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
        for _i in 0..arr_len {
            msg.data.push(1);
        }
        return msg;
    }

    let qs = qstring::QString::from(req.query_string());
    let size_str = qs.get("size").unwrap_or("1024");
    let mem_sz: usize = size_str.parse::<usize>().expect("parse err");

    let arr_message = gen_arr_message(mem_sz as _);
    let out_bytes: Vec<u8> = arr_message.write_to_bytes().expect("write err");
    Ok(HttpResponseBuilder::new(StatusCode::OK).body(out_bytes))
}