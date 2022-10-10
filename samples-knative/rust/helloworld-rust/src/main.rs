#![feature(
c_size_t,
core_intrinsics
)]
#![feature(get_mut_unchecked)]

use std::alloc::{GlobalAlloc};
use std::sync::{Arc, Mutex};
use actix_web::{App, HttpServer};
use jemalloc_sys::extent_hooks_s;

mod service;
mod util;
mod handler;
pub mod sys_env;
mod bindings;
mod allocator;

pub use allocator::*;
use crate::service::*;
use crate::util::*;

#[macro_use]
extern crate lazy_static;


use macros::declare_global;
use crate::sys_env::{fetch_env, server_port};

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

fn init() {}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();
    let addr = format!("127.0.0.1:{}", server_port());
    println!("listen on {}", addr);
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
    }).bind(addr)?
        .workers(12)
        .run()
        .await
}