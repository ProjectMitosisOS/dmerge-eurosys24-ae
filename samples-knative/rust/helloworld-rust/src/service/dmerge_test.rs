use std::time::{SystemTime, UNIX_EPOCH};
use actix_web::{get, HttpRequest, HttpResponse, HttpResponseBuilder, web};
use actix_web::http::StatusCode;
use serde_json::{json};

/// Fetch origin data
#[get("/dmerge/register")]
pub async fn dmerge_register(_req: HttpRequest,
                             mut _payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    let addr = 0x4ffff5a00000 as u64;
    let mem_sz = 1024 * 1024 * 512 as u64;

    // allocate heap
    unsafe {
        let _ptr = crate::bindings::create_heap(addr, mem_sz);
        crate::ALLOC::init(crate::AllocatorMaster::init(addr as _,
                                                        mem_sz));
        let all = crate::get_global_allocator_master_mut().get_thread_allocator();
        let _ptr = all.alloc(1024 * 1024 as libc::size_t, 0);
    }
    let res = unsafe {
        let sd = crate::bindings::sopen();
        crate::bindings::call_register(sd, addr as u64)
    };
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"status":res})))
}

#[get("/dmerge/pull")]
pub async fn dmerge_pull(req: HttpRequest,
                         mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    let qs = qstring::QString::from(req.query_string());
    let size_str = qs.get("size").unwrap_or("1024");
    let mem_sz: usize = size_str.parse::<usize>().expect("parse err");
    let addr = 0x4ffff5a00000 as u64;

    let sd = unsafe { crate::bindings::sopen() };
    unsafe {
        let gid = std::ffi::CString::new("fe80:0000:0000:0000:248a:0703:009c:7c94")
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
        let _res = crate::bindings::call_pull(sd);
    }
    let data_res = unsafe {
        let t = *(addr as *mut [u8; 1024]);
        let _sum = {
            let mut res: u64 = 0;
            for i in 0..mem_sz {
                res += t[i] as u64
            }
            res
        };
        t[1]
    };

    let end_tick = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards")
        .as_nanos();
    let passed_ns = end_tick - start_tick;
    println!("passed {} us", passed_ns / 1000);

    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"data":data_res})))
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

#[get("/protobuf/data")]
pub async fn protobuf_data(req: HttpRequest,
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