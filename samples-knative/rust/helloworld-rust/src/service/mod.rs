mod cloud_event;
mod data_flow;
mod dmerge_test;

pub use data_flow::*;
use cloudevents::{AttributesReader, AttributesWriter, Event, EventBuilder, EventBuilderV10};
use serde_json::json;
use actix_web::{get, post, web, HttpRequest, error, HttpResponse, HttpResponseBuilder};
use actix_web::http::StatusCode;
use cloudevents::binding::actix::{HttpRequestExt, HttpResponseBuilderExt};
use cloudevents::binding::reqwest::RequestBuilderExt;
use serde::{Deserialize, Serialize};
use futures::StreamExt;
use crate::handler::{handle_mapper, handle_reducer, handle_split};
use cloud_event::handle_ce;
pub use dmerge_test::*;

const MAX_SIZE: usize = 262_144;

#[post("/")]
pub async fn faas_entry(mut event: Event) -> Result<HttpResponse, actix_web::Error> {
    let source = event.source().as_str().to_string();
    let egress_ce_type = handle_ce(&mut event)?;

    event.set_source(source);
    event.set_type(egress_ce_type);
    HttpResponseBuilder::new(StatusCode::OK)
        .event(event)
}

#[get("/")]
pub async fn get_event() -> Event {
    let payload = json!({"hello": "world"});

    EventBuilderV10::new()
        .id("0001")
        .ty("example.test")
        .source("http://localhost/")
        .data("application/json", payload)
        .extension("someint", "10")
        .build()
        .unwrap()
}


#[get("/trigger")]
pub async fn trigger() -> Event {
    let payload = json!({"msg": "Hello World from the pod."});

    let client = reqwest::Client::new();
    let register_url = "http://broker-ingress.knative-eventing.svc.cluster.local/knative-samples/default";


    let event = EventBuilderV10::new()
        .id("0001")
        .ty("dev.knative.samples.helloworld")
        .source("knative/eventing/samples/faas")
        .data("application/json", payload)
        .extension("someint", "10")
        .build()
        .unwrap();

    let rep = client.post(register_url)
        .event(event.clone())
        .unwrap()
        .send()
        .await;
    if rep.is_ok() {
        println!("send res is ok:{:?}", rep);
    }

    event
}

#[derive(Serialize, Deserialize, Clone)]
pub struct MapperRequest {
    pub chunk_data: String,
}

#[derive(Serialize, Deserialize, Clone)]
pub struct ReducerRequest {
    pub sum: u32,
}

#[get("/split")]
pub async fn splitter() -> Result<HttpResponse, actix_web::Error> {
    handle_split().await;
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"user": "python"})))
}


#[post("/map")]
pub async fn mapper(req: HttpRequest,
                    mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    let mut body = web::BytesMut::new();
    while let Some(chunk) = payload.next().await {
        let chunk = chunk?;
        // limit max size of in-memory payload
        if (body.len() + chunk.len()) > MAX_SIZE {
            return Err(error::ErrorBadRequest("overflow"));
        }
        body.extend_from_slice(&chunk);
    }

    // body is loaded, now we can deserialize serde-json
    let obj = serde_json::from_slice::<MapperRequest>(&body)?;
    handle_mapper(&*obj.chunk_data).await;

    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"user": "mapper"})))
}

#[post("/reduce")]
pub async fn reducer(req: HttpRequest,
                     mut payload: web::Payload) -> Result<HttpResponse, actix_web::Error> {
    let mut body = web::BytesMut::new();
    while let Some(chunk) = payload.next().await {
        let chunk = chunk?;
        // limit max size of in-memory payload
        if (body.len() + chunk.len()) > MAX_SIZE {
            return Err(error::ErrorBadRequest("overflow"));
        }
        body.extend_from_slice(&chunk);
    }
    let obj = serde_json::from_slice::<ReducerRequest>(&body)?;

    handle_reducer(obj.sum);
    Ok(HttpResponseBuilder::new(StatusCode::OK)
        .json(json!({"user": "python"})))
}
