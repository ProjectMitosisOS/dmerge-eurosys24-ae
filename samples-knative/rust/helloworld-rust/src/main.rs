#![feature(async_closure)]

use actix_web::{App, HttpServer};

mod service;
mod util;
mod handler;

use crate::service::*;
use crate::util::*;

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // std::env::set_var("RUST_LOG", "actix_server=info,actix_web=info");
    env_logger::init();

    HttpServer::new(|| {
        App::new()
            .wrap(actix_cors::Cors::permissive())
            .wrap(actix_web::middleware::Logger::default())
            .service(post_event)
            .service(get_event)
            .service(splitter)
            .service(trigger)
            .service(mapper)
            .service(reducer)
    }).bind("127.0.0.1:8080")?
        .workers(12)
        .run()
        .await
}