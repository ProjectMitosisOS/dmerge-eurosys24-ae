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

#[inline]
pub unsafe fn push<T>(address: u64, data: &T) where T: Clone {
    *(address as *mut T) = data.clone();
}

#[inline]
pub unsafe fn read_data<T>(address: u64) -> T where T: Clone {
    (*(address as *mut T)).clone()
}


pub const DEFAULT_HEAP_BASE_ADDR: u64 = 0x4ffff5a00000;

pub unsafe fn init_heap(base_addr: u64, hint: usize, mem_sz: u64) {
    // allocate heap
    println!("create heap on addr: 0x{:x} with hint {}", base_addr, hint);
    let _ptr = crate::bindings::create_heap(base_addr, mem_sz * 2);
    crate::ALLOC::init(
        AllocatorMaster::init(base_addr as _,
                              mem_sz * 2));

    let _ptr = get_global_allocator_master_mut()
        .get_thread_allocator()
        .alloc((mem_sz) as libc::size_t, 0);

    let sd = crate::bindings::sopen();
    let _ = crate::bindings::call_register(sd, base_addr as u64, hint as _);
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();

    #[cfg(feature = "proto-dmerge")]
    unsafe {
        crate::init_heap(heap_base(), heap_hint(),
                         1024 * 1024 * 512);
    }

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