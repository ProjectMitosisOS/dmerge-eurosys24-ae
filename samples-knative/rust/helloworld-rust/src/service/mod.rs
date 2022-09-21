use cloudevents::{AttributesWriter, Event, EventBuilder, EventBuilderV10};
use serde_json::json;
use actix_web::{get, post, App, HttpServer};
use cloudevents::binding::reqwest::RequestBuilderExt;

#[post("/")]
pub async fn post_event(event: Event) -> Event {
    println!("Received Event: {:?}", event);
    event
}

#[get("/")]
pub async fn get_event() -> Event {
    let payload = json!({"hello": "worlds"});

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

    let payload = json!({"hello": "trigger"});
    event
}

#[get("/map")]
pub async fn mapper(mut event: Event) -> Event {
    let payload = json!({"hello": "world"});
    event.set_source("new source");
    event
}

#[post("/reduce")]
pub async fn reducer(mut event: Event) -> Event {
    event
}
