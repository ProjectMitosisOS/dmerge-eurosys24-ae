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

pub(crate) fn handle_ce(event: &mut Event) -> Result<String, actix_web::Error> {
    let (datacontenttype, dataschema, data) = event.take_data();

    // Handle body
    if let Some(data) = data {
        // TODO: deseri data
        let res = serde_json::Value::try_from(data).unwrap();
        // let u: MapperRequest = serde_json::from_value(res).unwrap();
    }
    match event.ty() {
        CE_SPLITTER => {}
        CE_MAPPER => {}
        CE_REDUCER => {}
        _ => {}
    };

    // Update egress event type
    let egress_ce_type = match env::var("CeType") {
        Ok(ce_type) => ce_type,
        _ => "ce-default".to_string()
    };
    Ok(egress_ce_type)
}