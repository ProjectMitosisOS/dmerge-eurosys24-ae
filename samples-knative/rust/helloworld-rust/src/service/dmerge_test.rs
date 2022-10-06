use actix_web::{get, HttpRequest, HttpResponse, HttpResponseBuilder, web};
use actix_web::http::StatusCode;
use libc::c_int;
use serde_json::json;

/// Fetch origin data
#[get("/dmerge/register")]
pub async fn dmerge_register(req: HttpRequest,
                             mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    let addr = 0x4ffff5a00000 as u64;

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
    let addr = 0x4ffff5a00000 as u64;

    let res = unsafe {
        let sd = crate::bindings::sopen();
        let res = crate::bindings::call_pull(sd);
        println!("addr value: {}", *(addr as *mut c_int) as u64);
        res
    };
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"status":res})))
}