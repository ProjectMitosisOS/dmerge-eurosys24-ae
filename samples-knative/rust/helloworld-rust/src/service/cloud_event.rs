use std::convert::TryFrom;
use std::{env, fmt, thread};
use std::error::Error;
use std::fmt::write;
use cloudevents::{AttributesReader, Event};
use serde_json::to_string;
use crate::MapperRequest;

const CE_SPLITTER: &str = "splitter";
const CE_MAPPER: &str = "mapper";
const CE_REDUCER: &str = "reducer";

fn handle_trigger() {
    println!("I'm in trigger");
}


fn handle_split() {
    println!("I'm in split");
}

fn handle_mapper() {
    println!("I'm in mapper");
}

fn handle_reducer() {
    println!("I'm in reducer");
}

pub(crate) fn handle_ce(event: &mut Event) -> Result<String, actix_web::Error> {
    println!("get ce {:?}", event);
    let (datacontenttype, dataschema, data) = event.take_data();

    // Handle body
    if let Some(data) = data {
        // TODO: deseri data
        let res = serde_json::Value::try_from(data).unwrap();
        // let u: MapperRequest = serde_json::from_value(res).unwrap();
    }
    // ingress ce type
    match event.ty() {
        CE_SPLITTER => {
            handle_split();
        }
        CE_MAPPER => {
            handle_mapper();
        }
        CE_REDUCER => {
            handle_reducer();
        }
        _ => {
            handle_trigger();
        }
    };

    // Update egress event type
    let egress_ce_type = match env::var("CeType") {
        Ok(ce_type) => ce_type,
        _ => "ce-default".to_string()
    };
    Ok(egress_ce_type)
}