use std::convert::TryFrom;
use std::{env};
use std::collections::HashMap;
use std::ffi::CString;
use std::time::{SystemTime, UNIX_EPOCH};
use cloudevents::{AttributesReader, Event};
use crate::service::payload::ExampleStruct;
use crate::sys_env::*;

const CE_SPLITTER: &str = "splitter";
const CE_MAPPER: &str = "mapper";
const CE_REDUCER: &str = "reducer";
const CE_SINK: &str = "sink";


const DATA_NW_ADDR_KEY: &str = "data_nw_addr";
const DATA_DATA_LOC_KEY: &str = "data_loc";
const DATA_HINT_KEY: &str = "heap_hint";

// Profiling
const PROFILE_START_TICK: &str = "start_tick";

/// Reply to next flow step with `data_nw_addr`, `data_loc`, to indicate the
/// network address and the data location
///
/// Access other knative service in same ns: https://github.com/knative/serving/issues/6155
/// TODO: Check Isio-injection in the https://knative.dev/docs/install/installing-istio
#[cfg(feature = "proto-json")]
fn handle_trigger(data: &HashMap<String, String>) -> HashMap<String, String> {
    // println!("I'm in trigger");
    let mut data = data.clone();

    // Fetch data for origin (in Json)
    let (service_name, revision, path) = (
        fetch_env(SERVICE_NAME_ENV_KEY, "default"),
        fetch_env(REVISION_ENV_KEY, "00001"),
        "/dataflow/fetch/origin");
    data.insert(DATA_NW_ADDR_KEY.to_string(),
                format!("http://{}-{}-private{}", service_name, revision, path));

    data.insert(DATA_DATA_LOC_KEY.to_string(), 2048.to_string());
    let since_the_epoch = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards");
    data.insert(PROFILE_START_TICK.to_string(), since_the_epoch.as_nanos().to_string());
    data
}

// Fetch data for origin (in Dmerge)
#[cfg(feature = "proto-dmerge")]
fn handle_trigger(data: &HashMap<String, String>) -> HashMap<String, String> {
    // FIXME: writing data
    let base_addr = heap_base();
    unsafe {
        let data_loc_address = base_addr;

        crate::push::<ExampleStruct>(data_loc_address,
                                     &ExampleStruct { number: 2412 });
    }

    let mut data = data.clone();

    // Gid as network address
    data.insert(DATA_NW_ADDR_KEY.to_string(),
                format!("fe80:0000:0000:0000:248a:0703:009c:7ca0"));
    // Base address
    data.insert(DATA_DATA_LOC_KEY.to_string(), base_addr.to_string());
    data.insert(DATA_HINT_KEY.to_string(), heap_hint().to_string());

    // Profiling data
    let since_the_epoch = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards");
    data.insert(PROFILE_START_TICK.to_string(), since_the_epoch.as_nanos().to_string());
    data
}

#[cfg(feature = "proto-json")]
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

#[cfg(feature = "proto-dmerge")]
fn handle_split(data: &HashMap<String, String>) -> HashMap<String, String> {
    let mut ret_data = data.clone();
    let base_addr = heap_base();
    if let Some(remote_nw_addr) = data.get(DATA_NW_ADDR_KEY) {
        let data_loc = if let Some(d) = data.get(DATA_DATA_LOC_KEY) {
            d.clone()
        } else { base_addr.to_string() };

        unsafe {
            // let hint = data.get(DATA_HINT_KEY)
            //     .unwrap_or(&String::from("73"))
            //     .parse::<usize>()
            //     .expect("not valid hint");
            let sd = crate::bindings::sopen();

            let data_loc_address = data_loc
                .parse::<u64>()
                .expect("not valid address pattern");
            let _ = crate::bindings::call_pull(sd, 73, 0);
            let example = crate::read_data::<ExampleStruct>(data_loc_address);
        }

        // Gid as network address
        ret_data.insert(DATA_NW_ADDR_KEY.to_string(),
                        remote_nw_addr.to_string());
        // Base address
        ret_data.insert(DATA_DATA_LOC_KEY.to_string(),
                        base_addr.to_string());
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

fn handle_sink(data: &HashMap<String, String>) -> HashMap<String, String> {
    let since_the_epoch = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards")
        .as_nanos();
    // Profile result
    let start_tick = data.get(PROFILE_START_TICK).expect("not found start tick");
    let start_tick: u128 = start_tick.trim().parse().unwrap();
    let offset = since_the_epoch - start_tick;
    println!("passed {} us", offset / 1000);
    data.clone()
}

pub(crate) fn handle_ce(event: &mut Event) -> Result<String, actix_web::Error> {
    // println!("get ce {:?}", event);
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
        CE_SINK => {
            handle_sink(&data_hash)
        }
        _ => {
            handle_trigger(&data_hash)
        }
    };
    let (_old_datacontenttype, _old_data) =
        event.set_data("application/json",
                       serde_json::to_string(&egress_data).unwrap());

    // Update egress event type
    let egress_ce_type = match env::var("EgressCeType") {
        Ok(ce_type) => ce_type,
        _ => "ce-default".to_string()
    };
    Ok(egress_ce_type)
}