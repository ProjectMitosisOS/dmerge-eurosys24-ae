#![feature(
c_size_t,
core_intrinsics
)]
#![feature(get_mut_unchecked)]

use actix_web::{App, HttpServer};

mod service;
mod handler;
pub mod sys_env;
mod bindings;
mod allocator;
mod proto_parser;

pub use allocator::*;
use crate::service::*;

extern crate lazy_static;


use macros::declare_global;
use crate::sys_env::*;

declare_global! {
    ALLOC,
    crate::allocator::AllocatorMaster
}

#[inline]
pub unsafe fn get_global_allocator_master_ref() -> &'static crate::AllocatorMaster {
    crate::ALLOC::get_ref()
}

#[inline]
pub unsafe fn get_global_allocator_master_mut() -> &'static mut crate::AllocatorMaster {
    crate::ALLOC::get_mut()
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();

    let addr = format!("127.0.0.1:{}", server_port());
    println!("App starting Listen on:{}", addr);
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
            .service(dmerge_register)
            .service(dmerge_pull)
            .service(json_micro)
            .service(json_data)
            .service(protobuf_data)
    }).bind(addr)?
        .workers(12)
        .run()
        .await
}