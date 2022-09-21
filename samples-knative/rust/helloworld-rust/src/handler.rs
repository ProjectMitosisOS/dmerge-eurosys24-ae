use std::collections::HashMap;
use std::thread;
use actix_web::HttpResponse;
use cloudevents::EventBuilderV10;
use reqwest::Response;

pub async fn handle_mapper() {
// pub async fn handle_mapper() -> Result<Response, reqwest::Error> {
    let mut map = HashMap::new();
    map.insert("lang", "rust");
    map.insert("body", "json");

    // let client = reqwest::Client::new();
    // client.post("http://httpbin.org/post")
    //     .json(&map)
    //     .send().await
}

pub fn handle_reducer() {}


// Example from https://doc.rust-lang.org/rust-by-example/std_misc/threads/testcase_mapreduce.html
pub fn mr_example() {
    use std::collections::HashMap;
    use std::thread;
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