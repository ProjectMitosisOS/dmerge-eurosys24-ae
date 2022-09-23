use actix_web::{App, HttpServer};

mod service;
mod util;
mod handler;
pub mod sys_env;

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