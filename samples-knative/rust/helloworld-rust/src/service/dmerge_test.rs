use std::intrinsics::size_of;
use std::time::{SystemTime, UNIX_EPOCH};
use actix_protobuf::ProtoBufResponseBuilder;
use actix_web::{get, HttpRequest, HttpResponse, HttpResponseBuilder, web};
use actix_web::http::StatusCode;
use serde_json::{json};



/// Fetch origin data
#[get("/dmerge/register")]
pub async fn dmerge_register(_req: HttpRequest,
                             mut _payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    unsafe {
        crate::init_heap(crate::DEFAULT_HEAP_BASE_ADDR, 1024 * 1024 * 512);
        let data_loc_address = crate::DEFAULT_HEAP_BASE_ADDR;
        *(data_loc_address as *mut usize) = 1025;
        let data_read = *(data_loc_address as *mut usize);
        println!("Register after...get data {}", data_read);
    }
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"status": 0})))
}

#[get("/dmerge/pull")]
pub async fn dmerge_pull(req: HttpRequest,
                         mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    let data_loc_address: u64 = 0x4ffff5a00000;
    let sd = unsafe { crate::bindings::sopen() };
    unsafe {
        let gid = std::ffi::CString::new("fe80:0000:0000:0000:248a:0703:009c:7ca0")
            .expect("not valid str");
        let mac_id = 0;
        crate::bindings::call_connect_session(sd,
                                              gid.as_ptr(),
                                              mac_id, 0);
    }

    let start_tick = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards")
        .as_nanos();
    unsafe {
        let res = crate::bindings::call_pull(sd);
        let data_read = *(data_loc_address as *mut u64);
        println!("Pull after...get data {}", data_read);
    }

    let end_tick = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards")
        .as_nanos();
    let passed_ns = end_tick - start_tick;
    println!("passed {} us", passed_ns / 1000);

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
    println!("passed {} us", passed_ns / 1000);
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"user": "python"})))
}

#[get("/json/data")]
pub async fn json_data(req: HttpRequest,
                       mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    let qs = qstring::QString::from(req.query_string());
    let size_str = qs.get("size").unwrap_or("1024");
    let mem_sz: usize = size_str.parse::<usize>().expect("parse err");

    let mut arr: Vec<u8> = Vec::with_capacity(mem_sz);
    for i in 0..mem_sz {
        arr.push((i % 128) as u8);
    }
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"tick": serde_json::to_string(&arr).expect("to string failed")})))
}
include!(concat!(env!("OUT_DIR"), "/protos/mod.rs"));
use protobuf::Message;
use crate::{AllocatorMaster, get_global_allocator_master_mut};

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