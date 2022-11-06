#![feature(
c_size_t,
core_intrinsics,
allocator_api,
get_mut_unchecked,
nonnull_slice_from_raw_parts,
alloc_layout_extra
)]

use std::mem::MaybeUninit;
use std::time::{SystemTime, UNIX_EPOCH};
use actix_web::{App, HttpServer};
use libc::memset;

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
use crate::service::payload::ExampleStruct;
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

// Should be freed manually
#[inline]
pub unsafe fn init_from_obj<T>() -> *mut T {
    jemalloc_alloc::<ExampleStruct>() as _
}

// Auto free
#[inline]
pub unsafe fn init_jemalloc_box<T>() -> Box<MaybeUninit<T>, JemallocAllocator> {
    Box::new_uninit_in(JemallocAllocator)
}

#[inline]
pub unsafe fn read_data<T>(address: u64) -> &'static mut T {
    &mut *(address as *mut T)
}


pub const DEFAULT_HEAP_BASE_ADDR: u64 = 0x4ffff5a00000;

#[cfg(test)]
mod tests {
    use std::sync::atomic::{compiler_fence, Ordering};
    use jemalloc_sys::mallocx;
    use libc::malloc;
    use super::*;

    // cargo test -- --nocapture
    // #[test]
    fn test_jemalloc_syscall() {
        use tokio::time::Instant;
        #[cfg(feature = "proto-dmerge")]
        unsafe {
            let base_addr = heap_base();
            let mem_sz = 1024 * 1024 * 32;
            let _ptr = crate::bindings::create_heap(base_addr, mem_sz);
            memset(base_addr as _, 0, mem_sz as _);
            crate::ALLOC::init(
                AllocatorMaster::init(base_addr as _,
                                      mem_sz));
            let allocator = get_global_allocator_master_mut()
                .get_thread_allocator();
        }

        let start = Instant::now();
        // Simple syscall
        let sd = unsafe { crate::bindings::sopen() };

        println!("passed {} us", (Instant::now() - start).as_micros());
        {
            let mut arr: Vec<u32, JemallocAllocator> = Vec::new_in(JemallocAllocator);
            for i in 0..1024 {
                arr.push(32);
            }
        }
    }

    #[test]
    fn test_jemalloc() {
        use crate::service::payload::ExampleStruct;

        unsafe {
            let base_addr = heap_base();
            let mem_sz = 1024 * 1024 * 32;
            let _ptr = crate::bindings::create_heap(base_addr, mem_sz);
            crate::ALLOC::init(
                AllocatorMaster::init(base_addr as _,
                                      mem_sz));
            for i in 0..12 {
                let bbox = crate::init_jemalloc_box::<ExampleStruct>();
                let data_loc_address
                    = bbox.as_ptr() as u64;

                let example = crate::read_data::<ExampleStruct>(data_loc_address);

                let mut vec: Vec<u32, JemallocAllocator> = Vec::new_in(JemallocAllocator);
                for i in 0..1024 {
                    vec.push(1);
                }
                // example.vec_data = vec;
                // println!("addr is 0x{:x}", data_loc_address as u64);
                // jemalloc_free(data_loc_address as _);
            }
        }
    }
}

pub unsafe fn init_heap(base_addr: u64, hint: usize, mem_sz: u64) {
    // allocate heap
    println!("create heap on addr: 0x{:x} with hint {}", base_addr, hint);
    let _ptr = crate::bindings::create_heap(base_addr, mem_sz);
    // touch all of the memory
    memset(base_addr as _, 0, mem_sz as _);
    crate::ALLOC::init(
        AllocatorMaster::init(base_addr as _,
                              mem_sz));
    // let _ptr = get_global_allocator_master_mut()
    //     .get_thread_allocator()
    //     .alloc(1 as libc::size_t, 0);

    let sd = crate::bindings::sopen();
    let _ = crate::bindings::call_register(sd, base_addr as u64, hint as _);
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();

    #[cfg(feature = "proto-dmerge")]
    unsafe {
        crate::init_heap(heap_base(), heap_hint(),
                         1024 * 1024 * 1024);
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