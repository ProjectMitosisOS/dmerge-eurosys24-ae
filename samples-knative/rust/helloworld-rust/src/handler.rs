use std::collections::HashMap;
use std::thread;
use crate::{MapperRequest, ReducerRequest};

pub async fn handle_split() {
    let data = "86967897737416471853297327050364959
11861322575564723963297542624962850
70856234701860851907960690014725639
38397966707106094172783238747669219
52380795257888236525459303330302837
58495327135744041048897885734297812
69920216438980873548808413720956532
16278424637452589860345374828574668";
    let chunked_data = data.split_whitespace();
    for (i, data_segment) in chunked_data.enumerate() {
        println!("data segment {} is \"{}\"", i, data_segment);
        thread::spawn(move || {
            // Calculate the intermediate sum of this segment:
            let _ = reqwest::blocking::Client::new()
                .post("http://localhost:8080/map")
                .json(&MapperRequest { chunk_data: String::from(data_segment) })
                .send();
        });
    }
}

pub async fn handle_mapper(data_segment: &str) {
    // Calculate the intermediate sum of this segment:
    let intermediate_sum = data_segment
        .chars()
        .map(|c| c.to_digit(10).expect("should be a digit"))
        .sum::<u32>();

    // send to reducer
    let client = reqwest::Client::new();
    // let js_payload = json!({"sum": intermediate_sum});
    let _ = client.post("http://localhost:8080/reduce")
        .json(&ReducerRequest { sum: intermediate_sum })
        .send().await;
}

pub fn handle_reducer(reducer_input: u32) {
    println!("processed segment result={}", reducer_input);
}


// Example from https://doc.rust-lang.org/rust-by-example/std_misc/threads/testcase_mapreduce.html
#[allow(dead_code)]
pub fn mr_example() {
    let mut map = HashMap::new();
    map.insert("lang", "rust");
    map.insert("body", "json");

    let data = "86967897737416471853297327050364959
11861322575564723963297542624962850
70856234701860851907960690014725639
38397966707106094172783238747669219
52380795257888236525459303330302837
58495327135744041048897885734297812
69920216438980873548808413720956532
16278424637452589860345374828574668";
    let chunked_data = data.split_whitespace();
    let mut children = vec![];
    for (i, data_segment) in chunked_data.enumerate() {
        println!("data segment {} is \"{}\"", i, data_segment);

        children.push(thread::spawn(move || -> u32 {
            // Calculate the intermediate sum of this segment:
            let result = data_segment
                .chars()
                .map(|c| c.to_digit(10).expect("should be a digit"))
                .sum();

            println!("processed segment {}, result={}", i, result);
            result
        }));
    }

    // Reduce phase (sum up)
    let final_result = children.into_iter().map(|c| c.join().unwrap()).sum::<u32>();

    println!("Final sum result: {}", final_result);
}