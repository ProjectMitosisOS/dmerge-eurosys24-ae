use std::convert::TryFrom;
use std::{env};
use std::collections::HashMap;
use cloudevents::{AttributesReader, Event};
use crate::sys_env::*;

const CE_SPLITTER: &str = "splitter";
const CE_MAPPER: &str = "mapper";
const CE_REDUCER: &str = "reducer";


const DATA_NW_ADDR_KEY: &str = "data_nw_addr";
const DATA_DATA_LOC_KEY: &str = "data_loc";

/// Reply to next flow step with `data_nw_addr`, `data_loc`, to indicate the
/// network address and the data location
///
/// Access other knative service in same ns: https://github.com/knative/serving/issues/6155
/// TODO: Check Isio-injection in the https://knative.dev/docs/install/installing-istio
fn handle_trigger(data: &HashMap<String, String>) -> HashMap<String, String> {
    // println!("I'm in trigger");
    let mut data = data.clone();

    let (service_name, revision, path) = (
        fetch_env(SERVICE_NAME_ENV_KEY, "default"),
        fetch_env(REVISION_ENV_KEY, "00001"),
        "/dataflow/fetch/origin");
    data.insert(DATA_NW_ADDR_KEY.to_string(),
                format!("http://{}-{}-private{}", service_name, revision, path));

    data.insert(DATA_DATA_LOC_KEY.to_string(), 2048.to_string());
    data
}


fn handle_split(data: &HashMap<String, String>) -> HashMap<String, String> {
    // println!("I'm in split, data:{:?}", data);
    let mut ret_data = data.clone();
    if let Some(remote_nw_addr) = data.get(DATA_NW_ADDR_KEY) {
        let data_loc = if let Some(d) = data.get(DATA_DATA_LOC_KEY) {
            d
        } else { "73" };
        let response = reqwest::blocking::Client::new()
            .get(remote_nw_addr)
            .query(&[("dataloc", data_loc)])
            .send()
            .expect("fail to get response")
            .text()
            .expect("fail to get text");

        println!("response:{}", response);


        // Assemble data flow meta
        let (service_name, revision, path) = (
            fetch_env(SERVICE_NAME_ENV_KEY, "default"),
            fetch_env(REVISION_ENV_KEY, "00001"),
            "/dataflow/fetch/split");
        ret_data.insert(DATA_NW_ADDR_KEY.to_string(),
                        format!("http://{}-{}-private{}", service_name, revision, path));

        ret_data.insert(DATA_DATA_LOC_KEY.to_string(), 4096.to_string());
    }
    ret_data
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