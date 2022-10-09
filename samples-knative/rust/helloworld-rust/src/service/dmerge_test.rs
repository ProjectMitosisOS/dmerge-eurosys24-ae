use std::time::{SystemTime, UNIX_EPOCH};
use actix_web::{get, HttpRequest, HttpResponse, HttpResponseBuilder, web};
use actix_web::http::StatusCode;
use libc::c_int;
use serde_json::json;

/// Fetch origin data
#[get("/dmerge/register")]
pub async fn dmerge_register(req: HttpRequest,
                             mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    let addr = 0x4ffff5a00000 as u64;
    let mem_sz = 1024 * 1024 * 1024 as u64;

    unsafe {
        let ptr = crate::bindings::create_heap(addr, mem_sz);
        crate::ALLOC::init(crate::AllocatorMaster::init(addr as _,
                                                        mem_sz));
        for i in 0..6 {
            let all = crate::get_global_allocator_master_mut().get_thread_allocator();
            let ptr = all.alloc(1024 * 4, 0);
            println!("[{}] addr 0x:{:x}", i, ptr as u64)
        }

        *(addr as *mut usize) = 1024;
    }
    let res = unsafe {
        let sd = crate::bindings::sopen();
        let res = crate::bindings::call_register(sd, addr as u64);
        *(addr as *mut c_int) = 4096;
        println!("register set value: {}", *(addr as *mut c_int) as u64);
        res
    };
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"status":res})))
}

#[get("/dmerge/pull")]
pub async fn dmerge_pull(req: HttpRequest,
                         mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    let start_tick = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards")
        .as_nanos();

    let addr = 0x4ffff5a00000 as u64;

    let res = unsafe {
        let sd = crate::bindings::sopen();
        let res = crate::bindings::call_pull(sd);
        let mut t = *(addr as *mut c_int) as u64;
        t += 1;
        res
    };

    let end_tick = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards")
        .as_nanos();
    let offset = end_tick - start_tick;
    println!("passed {} us", offset / 1000);

    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"status":res})))
}


#[get("/json/micro")]
pub async fn json_micro() -> Result<HttpResponse, actix_web::Error> {
    let start_tick = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards")
        .as_nanos();

    {
        let data = "86967897737416471853297327050364959";
        let chunked_data = data.split_whitespace();
        for (i, data_segment) in chunked_data.enumerate() {
            // println!("data segment {} is \"{}\"", i, data_segment);
            let _ = reqwest::Client::new()
                .post(format!("http://localhost:{}/map", crate::server_port()))
                .json(&crate::MapperRequest { chunk_data: String::from(data_segment) })
                .send().await;
            break;
        }
    }

    let end_tick = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards")
        .as_nanos();
    let offset = end_tick - start_tick;
    println!("passed {} us", offset / 1000);
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"user": "python"})))
}