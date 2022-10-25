use actix_web::{get, HttpRequest, HttpResponse, HttpResponseBuilder, web};
use actix_web::http::StatusCode;
use serde_json::json;
use qstring::QString;

const ORIGIN_DATA_STR: &str = "86967897737416471853297327050364959
11861322575564723963297542624962850
70856234701860851907960690014725639
38397966707106094172783238747669219
52380795257888236525459303330302837
58495327135744041048897885734297812
69920216438980873548808413720956532
16278424637452589860345374828574668";

/// Fetch origin data
#[get("/dataflow/fetch/origin")]
pub async fn df_fetch_origin(req: HttpRequest,
                             mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    let qs = QString::from(req.query_string());
    let data_loc = qs.get("dataloc")
        .ok_or(actix_web::error::ErrorInternalServerError("not found query string"))?;
    // println!("fetch inner df_fetch_origin, query dataloc:{}", data_loc);
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"data_type": "origin data", "data": ORIGIN_DATA_STR})))
}

/// Fetch data from split pods
#[get("/dataflow/fetch/split")]
pub async fn df_fetch_split(req: HttpRequest,
                            mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    println!("fetch inner df_fetch_split!");
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"data_type": "split data"})))
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