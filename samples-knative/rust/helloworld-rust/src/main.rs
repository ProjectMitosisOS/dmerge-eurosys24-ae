use actix_web::{App, HttpServer};

mod service;
mod util;
mod handler;
pub mod sys_env;
mod bindings;

use crate::service::*;
use crate::util::*;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let addr = 0x4ffff5a00000 as u64;
    let mem_sz = 1024 * 1024 * 1024 as u64;
    let ptr = unsafe { crate::bindings::create_heap(addr, mem_sz) };

    env_logger::init();

    HttpServer::new(|| {
        App::new()
            .wrap(actix_cors::Cors::permissive())
            .wrap(actix_web::middleware::Logger::default())
            .service(faas_entry)
            .service(get_event)
            .service(splitter)
            .service(trigger)
            .service(mapper)
            .service(reducer)
            .service(df_fetch_origin)
            .service(df_fetch_split)
            .service(df_fetch_mapper)
            .service(df_fetch_reducer)
    }).bind("127.0.0.1:8080")?
        .workers(12)
        .run()
        .await
}