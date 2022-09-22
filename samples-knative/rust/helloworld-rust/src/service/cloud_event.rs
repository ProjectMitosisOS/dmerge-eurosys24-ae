use std::convert::TryFrom;
use std::{env};
use std::collections::HashMap;
use cloudevents::{AttributesReader, Event};

const CE_SPLITTER: &str = "splitter";
const CE_MAPPER: &str = "mapper";
const CE_REDUCER: &str = "reducer";

fn handle_trigger(data: &HashMap<String, String>) -> HashMap<String, String> {
    println!("I'm in trigger");
    data.clone()
}


fn handle_split(data: &HashMap<String, String>) -> HashMap<String, String> {
    println!("I'm in split");
    data.clone()
}

fn handle_mapper(data: &HashMap<String, String>) -> HashMap<String, String> {
    println!("I'm in mapper");
    data.clone()
}

fn handle_reducer(data: &HashMap<String, String>) -> HashMap<String, String> {
    println!("I'm in reducer");
    data.clone()
}

pub(crate) fn handle_ce(event: &mut Event) -> Result<String, actix_web::Error> {
    println!("get ce {:?}", event);
    let (_, _, data) = event.take_data();

    let data_hash = if let Some(data) = data {
        let res = serde_json::Value::try_from(data).unwrap();
        let u: HashMap<String, String> = serde_json::from_value(res).unwrap();
        u
    } else {
        HashMap::<String, String>::new()
    };
    // ingress ce type
    let egress_data = match event.ty() {
        CE_SPLITTER => {
            handle_split(&data_hash)
        }
        CE_MAPPER => {
            handle_mapper(&data_hash)
        }
        CE_REDUCER => {
            handle_reducer(&data_hash)
        }
        _ => {
            handle_trigger(&data_hash)
        }
    };
    let (_old_datacontenttype, _old_data) =
        event.set_data("application/json",
                       serde_json::to_string(&egress_data).unwrap());

    // Update egress event type
    let egress_ce_type = match env::var("CeType") {
        Ok(ce_type) => ce_type,
        _ => "ce-default".to_string()
    };
    Ok(egress_ce_type)
}