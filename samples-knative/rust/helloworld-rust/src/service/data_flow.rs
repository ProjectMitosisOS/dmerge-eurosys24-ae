use actix_web::{get, HttpRequest, HttpResponse, HttpResponseBuilder, web};
use actix_web::http::StatusCode;
use serde_json::json;
use qstring::QString;

/// Fetch origin data
#[get("/dataflow/fetch/origin")]
pub async fn df_fetch_origin(req: HttpRequest,
                             mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    let qs = QString::from(req.query_string());
    let data_loc = qs.get("dataloc")
        .ok_or(actix_web::error::ErrorInternalServerError("not found query string"))?;
    println!("fetch inner df_fetch_origin, query dataloc:{}", data_loc);
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"user": "mapper"})))
}

/// Fetch data from split pods
#[get("/dataflow/fetch/split")]
pub async fn df_fetch_split(req: HttpRequest,
                            mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    println!("fetch inner df_fetch_split!");
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"user": "mapper"})))
}

/// Fetch data from mapper pods
#[get("/dataflow/fetch/mapper")]
pub async fn df_fetch_mapper(req: HttpRequest,
                             mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    unimplemented!()
}

/// Fetch data from reducer pods
#[get("/dataflow/fetch/reducer")]
pub async fn df_fetch_reducer(req: HttpRequest,
                              mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    unimplemented!()
}